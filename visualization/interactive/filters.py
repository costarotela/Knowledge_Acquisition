"""
Advanced filtering system for interactive dashboards.
"""
from typing import Dict, Any, List, Optional, Union, Callable
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pydantic import BaseModel

class FilterCondition(BaseModel):
    """Filter condition model."""
    field: str
    operator: str
    value: Any
    
    class Config:
        arbitrary_types_allowed = True

class FilterGroup(BaseModel):
    """Group of filter conditions."""
    conditions: List[FilterCondition]
    combine_operator: str = "and"  # "and" or "or"

class FilterSet(BaseModel):
    """Complete set of filters."""
    groups: List[FilterGroup]
    combine_operator: str = "and"  # "and" or "or"

class FilterOperator:
    """Filter operator implementations."""
    
    @staticmethod
    def equals(value: Any, target: Any) -> bool:
        return value == target
    
    @staticmethod
    def not_equals(value: Any, target: Any) -> bool:
        return value != target
    
    @staticmethod
    def greater_than(value: Any, target: Any) -> bool:
        return value > target
    
    @staticmethod
    def less_than(value: Any, target: Any) -> bool:
        return value < target
    
    @staticmethod
    def contains(value: str, target: str) -> bool:
        return target.lower() in value.lower()
    
    @staticmethod
    def starts_with(value: str, target: str) -> bool:
        return value.lower().startswith(target.lower())
    
    @staticmethod
    def ends_with(value: str, target: str) -> bool:
        return value.lower().endswith(target.lower())
    
    @staticmethod
    def in_range(value: Any, target: tuple) -> bool:
        start, end = target
        return start <= value <= end
    
    @staticmethod
    def in_list(value: Any, target: List) -> bool:
        return value in target
    
    @staticmethod
    def regex_match(value: str, target: str) -> bool:
        import re
        return bool(re.match(target, value))

class FilterEngine:
    """Engine for applying filters to data."""
    
    def __init__(self):
        """Initialize filter engine."""
        self.operators = {
            "eq": FilterOperator.equals,
            "neq": FilterOperator.not_equals,
            "gt": FilterOperator.greater_than,
            "lt": FilterOperator.less_than,
            "contains": FilterOperator.contains,
            "starts_with": FilterOperator.starts_with,
            "ends_with": FilterOperator.ends_with,
            "in_range": FilterOperator.in_range,
            "in_list": FilterOperator.in_list,
            "regex": FilterOperator.regex_match
        }
    
    def apply_condition(
        self,
        data: pd.DataFrame,
        condition: FilterCondition
    ) -> pd.Series:
        """Apply single filter condition."""
        if condition.operator not in self.operators:
            raise ValueError(f"Unsupported operator: {condition.operator}")
        
        if condition.field not in data.columns:
            raise ValueError(f"Field not found: {condition.field}")
        
        operator_func = self.operators[condition.operator]
        return data[condition.field].apply(
            lambda x: operator_func(x, condition.value)
        )
    
    def apply_group(
        self,
        data: pd.DataFrame,
        group: FilterGroup
    ) -> pd.Series:
        """Apply group of filter conditions."""
        if not group.conditions:
            return pd.Series([True] * len(data))
        
        results = []
        for condition in group.conditions:
            results.append(self.apply_condition(data, condition))
        
        if group.combine_operator == "and":
            return pd.concat(results, axis=1).all(axis=1)
        else:  # "or"
            return pd.concat(results, axis=1).any(axis=1)
    
    def apply_filters(
        self,
        data: pd.DataFrame,
        filter_set: FilterSet
    ) -> pd.DataFrame:
        """Apply complete set of filters."""
        if not filter_set.groups:
            return data
        
        results = []
        for group in filter_set.groups:
            results.append(self.apply_group(data, group))
        
        if filter_set.combine_operator == "and":
            mask = pd.concat(results, axis=1).all(axis=1)
        else:  # "or"
            mask = pd.concat(results, axis=1).any(axis=1)
        
        return data[mask]

class DynamicFilter:
    """Dynamic filter builder."""
    
    def __init__(self, data: pd.DataFrame):
        """Initialize dynamic filter."""
        self.data = data
        self.filter_set = FilterSet(groups=[])
    
    def add_text_filter(
        self,
        field: str,
        value: str,
        operator: str = "contains"
    ) -> "DynamicFilter":
        """Add text-based filter."""
        condition = FilterCondition(
            field=field,
            operator=operator,
            value=value
        )
        
        self.filter_set.groups.append(
            FilterGroup(conditions=[condition])
        )
        return self
    
    def add_numeric_filter(
        self,
        field: str,
        value: Union[int, float],
        operator: str = "eq"
    ) -> "DynamicFilter":
        """Add numeric filter."""
        condition = FilterCondition(
            field=field,
            operator=operator,
            value=value
        )
        
        self.filter_set.groups.append(
            FilterGroup(conditions=[condition])
        )
        return self
    
    def add_date_filter(
        self,
        field: str,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> "DynamicFilter":
        """Add date range filter."""
        if end_date is None:
            end_date = start_date + timedelta(days=1)
        
        condition = FilterCondition(
            field=field,
            operator="in_range",
            value=(start_date, end_date)
        )
        
        self.filter_set.groups.append(
            FilterGroup(conditions=[condition])
        )
        return self
    
    def add_categorical_filter(
        self,
        field: str,
        values: List[Any]
    ) -> "DynamicFilter":
        """Add categorical filter."""
        condition = FilterCondition(
            field=field,
            operator="in_list",
            value=values
        )
        
        self.filter_set.groups.append(
            FilterGroup(conditions=[condition])
        )
        return self
    
    def combine_last(
        self,
        n: int = 2,
        operator: str = "and"
    ) -> "DynamicFilter":
        """Combine last N filter groups."""
        if len(self.filter_set.groups) < n:
            return self
        
        groups_to_combine = self.filter_set.groups[-n:]
        combined_conditions = []
        
        for group in groups_to_combine:
            combined_conditions.extend(group.conditions)
        
        self.filter_set.groups = self.filter_set.groups[:-n]
        self.filter_set.groups.append(
            FilterGroup(
                conditions=combined_conditions,
                combine_operator=operator
            )
        )
        
        return self
    
    def apply(self) -> pd.DataFrame:
        """Apply all filters."""
        engine = FilterEngine()
        return engine.apply_filters(self.data, self.filter_set)

class SmartFilter:
    """Smart filter with automatic type detection."""
    
    def __init__(self, data: pd.DataFrame):
        """Initialize smart filter."""
        self.data = data
        self.filter = DynamicFilter(data)
    
    def add_filter(
        self,
        field: str,
        value: Any,
        operator: Optional[str] = None
    ) -> "SmartFilter":
        """Add filter with automatic type detection."""
        if field not in self.data.columns:
            raise ValueError(f"Field not found: {field}")
        
        dtype = self.data[field].dtype
        
        if pd.api.types.is_numeric_dtype(dtype):
            if operator is None:
                operator = "eq"
            self.filter.add_numeric_filter(field, value, operator)
            
        elif pd.api.types.is_datetime64_dtype(dtype):
            if isinstance(value, (list, tuple)):
                self.filter.add_date_filter(field, value[0], value[1])
            else:
                self.filter.add_date_filter(field, value)
                
        elif pd.api.types.is_categorical_dtype(dtype):
            if isinstance(value, (list, tuple)):
                self.filter.add_categorical_filter(field, value)
            else:
                self.filter.add_categorical_filter(field, [value])
                
        else:  # Treat as text
            if operator is None:
                operator = "contains"
            self.filter.add_text_filter(field, str(value), operator)
        
        return self
    
    def apply(self) -> pd.DataFrame:
        """Apply all filters."""
        return self.filter.apply()
