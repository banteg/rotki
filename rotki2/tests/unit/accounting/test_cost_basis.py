"""Unit tests for cost basis calculations"""
import pytest
from rotkehlchen.constants import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.types import CostBasisMethod, Price, Timestamp
from rotki2.accounting.cost_basis.calculator import (
    FIFOCostBasisMethod,
    LIFOCostBasisMethod,
    HIFOCostBasisMethod,
    AverageCostBasisMethod,
)
from rotki2.accounting.cost_basis.structures import AssetAcquisitionEvent
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_ETH


class TestFIFOCostBasis:
    """Test FIFO cost basis calculation"""
    
    def test_fifo_order(self):
        """Test that FIFO processes acquisitions in first-in-first-out order"""
        method = FIFOCostBasisMethod()
        
        # Add acquisitions
        event1 = AssetAcquisitionEvent(
            amount=FVal('10'),
            timestamp=Timestamp(1000),
            rate=Price(FVal('100')),
            index=0,
        )
        event2 = AssetAcquisitionEvent(
            amount=FVal('20'),
            timestamp=Timestamp(2000),
            rate=Price(FVal('200')),
            index=1,
        )
        
        method.add_in_event(event1)
        method.add_in_event(event2)
        
        # Check order - should get event1 first
        acquisitions = method.get_acquisitions()
        assert len(acquisitions) == 2
        assert acquisitions[0].timestamp == Timestamp(1000)
        assert acquisitions[1].timestamp == Timestamp(2000)


class TestLIFOCostBasis:
    """Test LIFO cost basis calculation"""
    
    def test_lifo_order(self):
        """Test that LIFO processes acquisitions in last-in-first-out order"""
        method = LIFOCostBasisMethod()
        
        # Add acquisitions
        event1 = AssetAcquisitionEvent(
            amount=FVal('10'),
            timestamp=Timestamp(1000),
            rate=Price(FVal('100')),
            index=0,
        )
        event2 = AssetAcquisitionEvent(
            amount=FVal('20'),
            timestamp=Timestamp(2000),
            rate=Price(FVal('200')),
            index=1,
        )
        
        method.add_in_event(event1)
        method.add_in_event(event2)
        
        # Check order - with LIFO, last added should be consumed first
        # The processing_iterator will yield event2 first
        events = list(method.processing_iterator())
        assert events[0].timestamp == Timestamp(2000)


class TestHIFOCostBasis:
    """Test HIFO cost basis calculation"""
    
    def test_hifo_order(self):
        """Test that HIFO processes acquisitions by highest rate first"""
        method = HIFOCostBasisMethod()
        
        # Add acquisitions with different rates
        event1 = AssetAcquisitionEvent(
            amount=FVal('10'),
            timestamp=Timestamp(1000),
            rate=Price(FVal('100')),
            index=0,
        )
        event2 = AssetAcquisitionEvent(
            amount=FVal('20'),
            timestamp=Timestamp(2000),
            rate=Price(FVal('300')),  # Higher rate
            index=1,
        )
        event3 = AssetAcquisitionEvent(
            amount=FVal('15'),
            timestamp=Timestamp(3000),
            rate=Price(FVal('200')),  # Medium rate
            index=2,
        )
        
        method.add_in_event(event1)
        method.add_in_event(event2)
        method.add_in_event(event3)
        
        # Check order - should process highest rate first
        events = list(method.processing_iterator())
        assert events[0].rate == Price(FVal('300'))  # Highest
        assert events[1].rate == Price(FVal('200'))  # Medium
        assert events[2].rate == Price(FVal('100'))  # Lowest


class TestAverageCostBasis:
    """Test Average Cost Basis calculation"""
    
    def test_average_cost_calculation(self):
        """Test that ACB correctly calculates average cost"""
        method = AverageCostBasisMethod()
        
        # Add first acquisition: 10 ETH @ 100 = 1000 total cost
        event1 = AssetAcquisitionEvent(
            amount=FVal('10'),
            timestamp=Timestamp(1000),
            rate=Price(FVal('100')),
            index=0,
        )
        method.add_in_event(event1)
        
        assert method.current_amount == FVal('10')
        assert method.current_total_acb == FVal('1000')
        
        # Add second acquisition: 20 ETH @ 200 = 4000 total cost
        event2 = AssetAcquisitionEvent(
            amount=FVal('20'),
            timestamp=Timestamp(2000),
            rate=Price(FVal('200')),
            index=1,
        )
        method.add_in_event(event2)
        
        # Total: 30 ETH, 5000 total cost
        assert method.current_amount == FVal('30')
        assert method.current_total_acb == FVal('5000')
        
        # Average cost should be 5000/30 = 166.67
        average_cost = method.current_total_acb / method.current_amount
        assert average_cost == FVal('5000') / FVal('30')