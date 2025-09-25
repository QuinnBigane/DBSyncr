"""
Filter Service
Handles data filtering and search operations for the GUI.
"""
import pandas as pd
from typing import Dict, Any, Optional, List, Set
from enum import Enum


class StatusFilter(Enum):
    """Enumeration of available status filters."""
    ALL_MATCHED = "All Matched"
    DB1_COMPLETE = "NS Data Complete"
    DB2_COMPLETE = "SF Data Complete"
    BOTH_COMPLETE = "Both Complete"


class FilterService:
    """Service for handling data filtering operations."""

    def __init__(self, data_service):
        self.data_service = data_service

    def apply_filters(
        self,
        search_text: str = "",
        status_filter: StatusFilter = StatusFilter.ALL_MATCHED,
        hide_synced_data: bool = False,
        visible_columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Apply comprehensive filters to the combined data.

        Args:
            search_text: Text to search in normalized keys
            status_filter: Status filter to apply
            hide_synced_data: Whether to hide rows with identical data
            visible_columns: List of columns to include (for column filtering)

        Returns:
            Filtered DataFrame
        """
        combined_data = self.data_service.get_combined_data()
        if combined_data is None or combined_data.empty:
            return pd.DataFrame()

        # Start with all data
        filtered_data = combined_data.copy()

        # Filter to show only matched records (items that exist in both databases)
        db1_name, db2_name = self.data_service.get_database_names()
        db1_key_col = f'{db1_name}_Key'
        db2_key_col = f'{db2_name}_Key'

        # Only include records that exist in both databases
        filtered_data = filtered_data[
            filtered_data[db1_key_col].notna() & filtered_data[db2_key_col].notna()
        ]

        # Apply search filter
        if search_text.strip():
            filtered_data = self._apply_search_filter(filtered_data, search_text.strip())

        # Apply status filter
        if status_filter != StatusFilter.ALL_MATCHED:
            filtered_data = self._apply_status_filter(filtered_data, status_filter, db1_name, db2_name)

        # Apply hide synced data filter
        if hide_synced_data:
            filtered_data = self._filter_out_synced_data(filtered_data, db1_name, db2_name)

        # Apply column visibility filter
        if visible_columns:
            filtered_data = self._apply_column_filter(filtered_data, visible_columns)

        return filtered_data

    def _apply_search_filter(self, data: pd.DataFrame, search_text: str) -> pd.DataFrame:
        """Apply search filter to normalized keys."""
        return data[
            data['NormalizedKey'].astype(str).str.contains(
                search_text, case=False, na=False
            )
        ]

    def _apply_status_filter(
        self,
        data: pd.DataFrame,
        status_filter: StatusFilter,
        db1_name: str,
        db2_name: str
    ) -> pd.DataFrame:
        """Apply status filter based on data completeness."""

        # Find weight columns (as an example of data completeness)
        db1_weight_cols = [col for col in data.columns if col.startswith(f'{db1_name}_') and 'Weight' in col]
        db2_weight_cols = [col for col in data.columns if col.startswith(f'{db2_name}_') and 'Weight' in col]

        if not db1_weight_cols or not db2_weight_cols:
            return data  # No weight columns found, return unchanged

        db1_weight_col = db1_weight_cols[0]
        db2_weight_col = db2_weight_cols[0]

        if status_filter == StatusFilter.DB1_COMPLETE:
            # Show items where DB1 has data but DB2 doesn't
            return data[data[db1_weight_col].notna() & data[db2_weight_col].isna()]
        elif status_filter == StatusFilter.DB2_COMPLETE:
            # Show items where DB2 has data but DB1 doesn't
            return data[data[db2_weight_col].notna() & data[db1_weight_col].isna()]
        elif status_filter == StatusFilter.BOTH_COMPLETE:
            # Show items where both have data
            return data[data[db1_weight_col].notna() & data[db2_weight_col].notna()]
        else:
            return data

    def _filter_out_synced_data(self, data: pd.DataFrame, db1_name: str, db2_name: str) -> pd.DataFrame:
        """Filter out rows where both databases have identical synced data."""
        # This is a simplified implementation - in practice, you'd compare
        # relevant business fields to determine if data is "synced"
        # For now, we'll consider rows where key fields match as potentially synced

        # Get comparable columns (non-key columns that exist in both DBs)
        db1_cols = [col for col in data.columns if col.startswith(f'{db1_name}_')]
        db2_cols = [col for col in data.columns if col.startswith(f'{db2_name}_')]

        # Remove synced rows (simplified logic)
        # In a real implementation, this would compare business-relevant fields
        synced_mask = data[db1_cols[0]].notna() & data[db2_cols[0]].notna()

        return data[~synced_mask]

    def _apply_column_filter(self, data: pd.DataFrame, visible_columns: List[str]) -> pd.DataFrame:
        """Filter DataFrame to only include visible columns."""
        # Always include essential columns
        essential_cols = ['Select', 'NormalizedKey']
        all_cols = essential_cols + [col for col in visible_columns if col in data.columns]

        return data[all_cols] if all_cols else data

    def get_filter_statistics(self, filtered_data: pd.DataFrame) -> Dict[str, Any]:
        """Get statistics about the filtered data."""
        if filtered_data is None or filtered_data.empty:
            return {
                'total_items': 0,
                'matched_items': 0,
                'db1_complete': 0,
                'db2_complete': 0,
                'both_complete': 0
            }

        db1_name, db2_name = self.data_service.get_database_names()

        # Get weight columns for completeness stats
        db1_weight_cols = [col for col in filtered_data.columns if col.startswith(f'{db1_name}_') and 'Weight' in col]
        db2_weight_cols = [col for col in filtered_data.columns if col.startswith(f'{db2_name}_') and 'Weight' in col]

        stats = {
            'total_items': len(filtered_data),
            'matched_items': len(filtered_data)
        }

        if db1_weight_cols and db2_weight_cols:
            db1_weight_col = db1_weight_cols[0]
            db2_weight_col = db2_weight_cols[0]

            stats.update({
                'db1_complete': len(filtered_data[filtered_data[db1_weight_col].notna() & filtered_data[db2_weight_col].isna()]),
                'db2_complete': len(filtered_data[filtered_data[db2_weight_col].notna() & filtered_data[db1_weight_col].isna()]),
                'both_complete': len(filtered_data[filtered_data[db1_weight_col].notna() & filtered_data[db2_weight_col].notna()])
            })
        else:
            stats.update({
                'db1_complete': 0,
                'db2_complete': 0,
                'both_complete': 0
            })

        return stats