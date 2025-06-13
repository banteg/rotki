"""Async network utilities using httpx for replacing synchronous requests."""
import json
import logging
from collections.abc import Callable
from http import HTTPStatus
from typing import Any, Literal, overload

import anyio
import httpx

from rotkehlchen.constants import GLOBAL_REQUESTS_TIMEOUT
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def create_async_session(max_backoff_secs: float = 30) -> httpx.AsyncClient:
    """Create an async httpx client configured to retry on connection, read, and
    specific server errors.
    
    Similar to the synchronous create_session but using httpx for async operations.
    """
    # httpx doesn't have built-in retry like requests, so we'll implement it in retry_calls_async
    return httpx.AsyncClient(
        timeout=httpx.Timeout(GLOBAL_REQUESTS_TIMEOUT),
        follow_redirects=True,
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
    )


async def request_get_async(
    url: str,
    timeout: int = GLOBAL_REQUESTS_TIMEOUT,
    handle_429: bool = False,
    backoff_in_seconds: float = 0,
) -> dict | list:
    """Async version of request_get using httpx.
    
    May raise:
    - UnableToDecryptRemoteData from request_get
    - Remote error if the get request fails
    """
    log.debug(f'Querying {url}')
    
    async with create_async_session() as client:
        response = await retry_calls_async(
            times=CachedSettings().get_query_retry_limit(),
            location='',
            handle_429=handle_429,
            backoff_in_seconds=backoff_in_seconds,
            method_name=url,
            function=client.get,
            # function's arguments
            url=url,
            timeout=timeout,
        )

    if response.status_code != HTTPStatus.OK:
        raise RemoteError(f'{url} returned status: {response.status_code}')

    try:
        result = json.loads(response.text)
    except json.decoder.JSONDecodeError as e:
        raise UnableToDecryptRemoteData(f'{url} returned malformed json. Error: {e!s}') from e

    return result


async def request_get_dict_async(
    url: str,
    timeout: int = GLOBAL_REQUESTS_TIMEOUT,
    handle_429: bool = False,
    backoff_in_seconds: float = 0,
) -> dict:
    """Like request_get_async, but the endpoint only returns a dict
    
    May raise:
    - UnableToDecryptRemoteData from request_get
    - Remote error if the get request fails
    """
    response = await request_get_async(url, timeout, handle_429, backoff_in_seconds)
    assert isinstance(response, dict)
    return response


async def retry_calls_async(
    times: int,
    location: str,
    handle_429: bool,
    backoff_in_seconds: float,
    method_name: str,
    function: Callable[..., Any],
    **kwargs: Any,
) -> Any:
    """Async version of retry_calls using anyio for sleeping.
    
    Calls an async function that deals with external apis for a given number of times
    until it fails or until it succeeds.
    
    If it fails with an acceptable error then we wait for a bit until the next try.
    
    Can also handle 429 errors with a specific backoff in seconds if required.
    
    - Raises RemoteError if there is something wrong with contacting the remote
    """
    tries = times
    while True:
        try:
            result = await function(**kwargs)

            if handle_429 and result.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                if tries == 0:
                    raise RemoteError(
                        f'{location} query for {method_name} failed after {times} tries',
                    )

                log.debug(
                    f'In retry_call for {location}-{method_name}. Got 429. Backing off for '
                    f'{backoff_in_seconds} seconds',
                )
                await anyio.sleep(backoff_in_seconds)
                tries -= 1
                continue

            return result

        except httpx.RequestError as e:
            tries -= 1
            log.debug(
                f'In retry_call for {location}-{method_name}. Got error {e!s} '
                f'Trying again ... with {tries} tries left',
            )
            if tries == 0:
                raise RemoteError(
                    f'{location} query for {method_name} failed after {times} tries. Reason: {e}'
                ) from e


@overload
async def query_file_async(url: str, is_json: Literal[True]) -> dict[str, Any]:
    ...


@overload
async def query_file_async(url: str, is_json: Literal[False]) -> str:
    ...


async def query_file_async(url: str, is_json: bool = False) -> str | dict[str, Any]:
    """Async version of query_file using httpx.
    
    Query the given file url and return the contents of the file
    May raise:
    - RemoteError if it was not possible to query the remote or the file is not a valid json file
    and is_json is set to true.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url=url, timeout=CachedSettings().get_timeout_tuple()[0])
    except httpx.RequestError as e:
        raise RemoteError(f'Failed to query file {url} due to: {e!s}') from e

    if response.status_code != 200:
        raise RemoteError(
            message=(
                f'File query for {url} failed with status code '
                f'{response.status_code} and text: {response.text}'
            ),
            error_code=response.status_code,
        )

    if is_json is True:
        try:
            return response.json()
        except json.decoder.JSONDecodeError as e:
            raise RemoteError(f'Queried file {url} is not a valid json file') from e

    return response.text