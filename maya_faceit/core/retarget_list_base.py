# retarget_list_base.py
# Maya Faceit Plugin - Retarget List Base Classes
# Converted from Blender to Maya Python 3.11

"""
Retarget list base classes for Faceit Maya plugin.
Provides base classes for retargeting UI lists and operations.
"""

import maya.cmds as cmds
from typing import List, Dict, Optional, Tuple, Any, Callable
import fnmatch

from .faceit_data import get_face_region_items
from .faceit_utils import get_faceit_objects_list
from .retarget_list_utils import (
    get_all_set_target_shapes,
    get_index_of_collection_item,
    get_index_of_parent_collection_item,
    get_target_shape_keys,
    get_invalid_target_shapes,
    are_target_shapes_valid,
    is_target_shape_double,
    set_base_regions_from_dict,
    target_shape_key_in_registered_objects,
)
from .shape_key_utils import (
    get_shape_key_names_from_objects,
    set_slider_max,
)


# ============================================================
# Target Shapes Property Class
# ============================================================

class TargetShapes:
    """
    Target shapes property class.
    Represents a single target shape in a retarget list.
    """
    
    def __init__(self, name: str = '---'):
        """
        Initialize a target shape.
        
        Args:
            name: Name of the target shape
        """
        self.name = name
    
    def to_dict(self) -> Dict:
        """
        Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {'name': self.name}
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TargetShapes':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary data
            
        Returns:
            TargetShapes instance
        """
        return cls(data.get('name', '---'))


# ============================================================
# Retarget Shapes Base Class
# ============================================================

class RetargetShapesBase:
    """
    Base class for retarget shapes.
    Represents a source shape with target shape mappings.
    """
    
    def __init__(self, name: str = ''):
        """
        Initialize a retarget shape.
        
        Args:
            name: Source shape name
        """
        self.name = name
        self.target_list_index = 0
        self.target_shapes: List[TargetShapes] = []
        self.amplify = 1.0
        self.use_animation = True
        self.region = 'other'
        self.display_name = name
    
    def to_dict(self) -> Dict:
        """
        Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'name': self.name,
            'display_name': self.display_name,
            'target_list_index': self.target_list_index,
            'target_shapes': [t.to_dict() for t in self.target_shapes],
            'amplify': self.amplify,
            'use_animation': self.use_animation,
            'region': self.region,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RetargetShapesBase':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary data
            
        Returns:
            RetargetShapesBase instance
        """
        item = cls(data.get('name', ''))
        item.display_name = data.get('display_name', item.name)
        item.target_list_index = data.get('target_list_index', 0)
        item.amplify = data.get('amplify', 1.0)
        item.use_animation = data.get('use_animation', True)
        item.region = data.get('region', 'other')
        
        for ts_data in data.get('target_shapes', []):
            item.target_shapes.append(TargetShapes.from_dict(ts_data))
        
        return item
    
    def add_target_shape(self, name: str) -> bool:
        """
        Add a target shape.
        
        Args:
            name: Target shape name
            
        Returns:
            True if added successfully
        """
        # Check if already exists
        for ts in self.target_shapes:
            if ts.name == name:
                return False
        
        self.target_shapes.append(TargetShapes(name))
        return True
    
    def remove_target_shape(self, name: str) -> bool:
        """
        Remove a target shape.
        
        Args:
            name: Target shape name
            
        Returns:
            True if removed successfully
        """
        for i, ts in enumerate(self.target_shapes):
            if ts.name == name:
                self.target_shapes.pop(i)
                return True
        
        return False
    
    def clear_target_shapes(self) -> None:
        """Clear all target shapes."""
        self.target_shapes.clear()
    
    def get_target_shape_names(self) -> List[str]:
        """
        Get all target shape names.
        
        Returns:
            List of target shape names
        """
        return [ts.name for ts in self.target_shapes]
    
    def is_valid(self, objects: List[str] = None) -> bool:
        """
        Check if all target shapes are valid.
        
        Args:
            objects: List of mesh objects to check
            
        Returns:
            True if all target shapes are valid
        """
        if not self.target_shapes:
            return False
        
        if objects is None:
            objects = get_faceit_objects_list()
        
        available_shapes = []
        for obj in objects:
            if not cmds.objExists(obj):
                continue
            
            history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
            for node in history:
                if cmds.nodeType(node) == 'blendShape':
                    targets = cmds.listAttr(f"{node}.weight", multi=True) or []
                    for target in targets:
                        if not target.startswith('weight'):
                            available_shapes.append(target)
        
        for ts in self.target_shapes:
            if ts.name not in available_shapes:
                return False
        
        return True
    
    def get_invalid_targets(self, objects: List[str] = None) -> List[str]:
        """
        Get invalid target shapes.
        
        Args:
            objects: List of mesh objects to check
            
        Returns:
            List of invalid target shape names
        """
        if objects is None:
            objects = get_faceit_objects_list()
        
        available_shapes = []
        for obj in objects:
            if not cmds.objExists(obj):
                continue
            
            history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
            for node in history:
                if cmds.nodeType(node) == 'blendShape':
                    targets = cmds.listAttr(f"{node}.weight", multi=True) or []
                    for target in targets:
                        if not target.startswith('weight'):
                            available_shapes.append(target)
        
        invalid = []
        for ts in self.target_shapes:
            if ts.name not in available_shapes:
                invalid.append(ts.name)
        
        return invalid


# ============================================================
# Face Regions Base Class
# ============================================================

class FaceRegionsBase:
    """
    Base class for face regions filtering.
    """
    
    def __init__(self):
        """Initialize face regions."""
        self.eyes = True
        self.brows = True
        self.cheeks = True
        self.nose = True
        self.mouth = True
        self.tongue = True
        self.other = True
    
    def get_active_regions(self) -> Dict[str, bool]:
        """
        Get all active regions.
        
        Returns:
            Dictionary mapping region names to active state
        """
        return {
            'eyes': self.eyes,
            'brows': self.brows,
            'cheeks': self.cheeks,
            'nose': self.nose,
            'mouth': self.mouth,
            'tongue': self.tongue,
            'other': self.other,
        }
    
    def set_active_regions(self, regions_dict: Dict[str, bool]) -> None:
        """
        Set active regions from a dictionary.
        
        Args:
            regions_dict: Dictionary mapping region names to active state
        """
        for region, value in regions_dict.items():
            if hasattr(self, region):
                setattr(self, region, value)
    
    def to_dict(self) -> Dict[str, bool]:
        """
        Convert to dictionary.
        
        Returns:
            Dictionary of region states
        """
        return self.get_active_regions()
    
    @classmethod
    def from_dict(cls, data: Dict[str, bool]) -> 'FaceRegionsBase':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary of region states
            
        Returns:
            FaceRegionsBase instance
        """
        regions = cls()
        for key, value in data.items():
            if hasattr(regions, key):
                setattr(regions, key, value)
        return regions


# ============================================================
# Reset Regions Operator Base
# ============================================================

class ResetRegionsOperatorBase:
    """
    Base class for resetting region filters.
    """
    
    name = "ResetRegionsOperator"
    label = "Reset Regions Filter"
    
    @staticmethod
    def get_face_regions() -> FaceRegionsBase:
        """
        Get face regions from scene data.
        
        Returns:
            FaceRegionsBase instance
        """
        if cmds.objExists("faceit_region_data"):
            data_str = cmds.getAttr("faceit_region_data.regions") or "{}"
            try:
                import json
                data = json.loads(data_str)
                return FaceRegionsBase.from_dict(data)
            except:
                pass
        
        return FaceRegionsBase()
    
    @staticmethod
    def save_face_regions(regions: FaceRegionsBase) -> bool:
        """
        Save face regions to scene data.
        
        Args:
            regions: FaceRegionsBase instance
            
        Returns:
            True if successful
        """
        if not cmds.objExists("faceit_region_data"):
            cmds.createNode("transform", name="faceit_region_data")
            cmds.addAttr("faceit_region_data", ln="regions", dt="string")
        
        try:
            import json
            data_str = json.dumps(regions.to_dict())
            cmds.setAttr("faceit_region_data.regions", data_str, type="string")
            return True
        except:
            return False
    
    def execute(self) -> bool:
        """
        Reset regions to default values.
        
        Returns:
            True if successful
        """
        regions = FaceRegionsBase()
        
        # Set all to True
        for attr in ['eyes', 'brows', 'cheeks', 'nose', 'mouth', 'tongue', 'other']:
            setattr(regions, attr, True)
        
        return self.save_face_regions(regions)


# ============================================================
# Set Default Regions Operator Base
# ============================================================

class SetDefaultRegionsBase:
    """
    Base class for setting default regions.
    """
    
    name = "SetDefaultRegions"
    label = "Set Default Regions"
    
    @staticmethod
    def get_retarget_shapes() -> List[RetargetShapesBase]:
        """
        Get retarget shapes from scene data.
        
        Returns:
            List of RetargetShapesBase instances
        """
        retarget_data = []
        
        if cmds.objExists("faceit_retarget_data"):
            data_str = cmds.getAttr("faceit_retarget_data.retarget_data") or "[]"
            try:
                import json
                data = json.loads(data_str)
                for item_data in data:
                    retarget_data.append(RetargetShapesBase.from_dict(item_data))
            except:
                pass
        
        return retarget_data
    
    @staticmethod
    def save_retarget_shapes(shapes: List[RetargetShapesBase]) -> bool:
        """
        Save retarget shapes to scene data.
        
        Args:
            shapes: List of RetargetShapesBase instances
            
        Returns:
            True if successful
        """
        if not cmds.objExists("faceit_retarget_data"):
            cmds.createNode("transform", name="faceit_retarget_data")
            cmds.addAttr("faceit_retarget_data", ln="retarget_data", dt="string")
        
        try:
            import json
            data = [s.to_dict() for s in shapes]
            data_str = json.dumps(data)
            cmds.setAttr("faceit_retarget_data.retarget_data", data_str, type="string")
            return True
        except:
            return False
    
    def execute(self) -> bool:
        """
        Set default regions for all retarget shapes.
        
        Returns:
            True if successful
        """
        shapes = self.get_retarget_shapes()
        
        # Use faceit_data region mapping
        from .faceit_data import FACE_REGIONS_BASE
        
        for shape in shapes:
            # Find region for this shape
            found_region = 'other'
            for region, shape_names in FACE_REGIONS_BASE.items():
                if shape.name in shape_names:
                    found_region = region
                    break
                # Also check if shape name contains region shape name
                for sn in shape_names:
                    if sn in shape.name or shape.name in sn:
                        found_region = region
                        break
                if found_region != 'other':
                    break
            
            shape.region = found_region
        
        return self.save_retarget_shapes(shapes)


# ============================================================
# Draw Regions Filter Base
# ============================================================

class DrawRegionsFilterBase:
    """
    Base class for drawing region filters in UI.
    """
    
    name = "DrawRegionsFilter"
    label = "Filter Regions"
    
    @staticmethod
    def get_face_regions() -> FaceRegionsBase:
        """
        Get face regions from scene data.
        
        Returns:
            FaceRegionsBase instance
        """
        return ResetRegionsOperatorBase.get_face_regions()
    
    @staticmethod
    def save_face_regions(regions: FaceRegionsBase) -> bool:
        """
        Save face regions to scene data.
        
        Args:
            regions: FaceRegionsBase instance
            
        Returns:
            True if successful
        """
        return ResetRegionsOperatorBase.save_face_regions(regions)
    
    def draw(self, layout_func: Callable) -> None:
        """
        Draw the region filter UI.
        
        Args:
            layout_func: Function to draw UI elements
        """
        face_regions = self.get_face_regions()
        
        # Draw region buttons
        regions = [
            ('brows', 'Brows'),
            ('eyes', 'Eyes'),
            ('cheeks', 'Cheeks'),
            ('nose', 'Nose'),
            ('mouth', 'Mouth'),
            ('tongue', 'Tongue'),
            ('other', 'Other'),
        ]
        
        for attr, label in regions:
            value = getattr(face_regions, attr, True)
            icon = 'HIDE_OFF' if value else 'HIDE_ON'
            # Call layout function to draw each region
            layout_func(attr, label, icon, value)
    
    def execute(self) -> bool:
        """
        Execute the operator.
        
        Returns:
            True if successful
        """
        return True


# ============================================================
# Retargeting Base Class
# ============================================================

class RetargetingBase:
    """
    Base class for retargeting operations.
    """
    
    name = "RetargetingBase"
    label = "Retargeting"
    
    # Operator names for subclasses to override
    edit_target_shapes_operator = ''
    remove_target_shapes_operator = ''
    clear_target_shapes_operator = ''
    draw_target_shapes_operator = ''
    
    @classmethod
    def get_retarget_shapes(cls) -> List[RetargetShapesBase]:
        """
        Get retarget shapes from scene data.
        
        Returns:
            List of RetargetShapesBase instances
        """
        return SetDefaultRegionsBase.get_retarget_shapes()
    
    @classmethod
    def save_retarget_shapes(cls, shapes: List[RetargetShapesBase]) -> bool:
        """
        Save retarget shapes to scene data.
        
        Args:
            shapes: List of RetargetShapesBase instances
            
        Returns:
            True if successful
        """
        return SetDefaultRegionsBase.save_retarget_shapes(shapes)
    
    @classmethod
    def poll(cls) -> bool:
        """
        Check if the operator can run.
        
        Returns:
            True if retarget shapes exist
        """
        return bool(cls.get_retarget_shapes())


# ============================================================
# Retarget Shapes List Base
# ============================================================

class RetargetShapesListBase:
    """
    Base class for retarget shapes UI list.
    """
    
    name = "RetargetShapesList"
    label = "Retarget Shapes"
    
    # Operator names for subclasses to override
    edit_target_shapes_operator = ''
    draw_target_shapes_operator = ''
    clear_target_shapes_operator = ''
    draw_region_filter_operator = ''
    reset_regions_filter_operator = ''
    
    # Settings
    show_use_animation = False
    property_name = 'name'
    show_assigned_regions = False
    use_filter_name_reverse = False
    filter_name = ''
    use_filter_sort_alpha = False
    use_filter_sort_reverse = False
    
    def __init__(self):
        """Initialize the list."""
        self.bitflag_filter_item = 1 << 0
    
    def draw_active(self, item: RetargetShapesBase) -> bool:
        """
        Check if an item should be drawn as active.
        
        Args:
            item: Retarget shape item
            
        Returns:
            True if active
        """
        return bool(item.use_animation and item.target_shapes)
    
    def get_display_text_target_shapes(self, item: RetargetShapesBase) -> str:
        """
        Get display text for target shapes.
        
        Args:
            item: Retarget shape item
            
        Returns:
            Display text
        """
        if not item.target_shapes:
            return '---'
        
        names = [ts.name for ts in item.target_shapes]
        return ', '.join(names[:3]) + ('...' if len(names) > 3 else '')
    
    @staticmethod
    def get_face_regions() -> FaceRegionsBase:
        """
        Get face regions from scene data.
        
        Returns:
            FaceRegionsBase instance
        """
        return ResetRegionsOperatorBase.get_face_regions()
    
    def draw_item(
        self,
        layout_func: Callable,
        item: RetargetShapesBase,
        index: int
    ) -> None:
        """
        Draw a single item in the list.
        
        Args:
            layout_func: Function to draw UI elements
            item: Retarget shape item
            index: Item index
        """
        target_shapes_valid = item.is_valid()
        
        # Draw the item
        layout_func(item, index, target_shapes_valid, self)
    
    def draw_filter(self, layout_func: Callable) -> None:
        """
        Draw the filter UI.
        
        Args:
            layout_func: Function to draw UI elements
        """
        # Name filter
        layout_func('filter_name', self.filter_name, 'Filter by name...')
        
        # Region filter
        face_regions = self.get_face_regions()
        layout_func('region_filter', face_regions)
        
        # Sort options
        layout_func('sort_options', self.use_filter_sort_alpha, self.use_filter_sort_reverse)
    
    def filter_items_by_name(
        self,
        pattern: str,
        bitflag: int,
        items: List[RetargetShapesBase],
        propname: str = "name",
        flags: List[int] = None,
        reverse: bool = False
    ) -> List[int]:
        """
        Filter items by name.
        
        Args:
            pattern: Filter pattern
            bitflag: Bit flag for filtering
            items: List of items
            propname: Property name to filter on
            flags: Existing flags
            reverse: Reverse filter
            
        Returns:
            List of flags
        """
        if not pattern or not items:
            return flags or []
        
        if flags is None:
            flags = [0] * len(items)
        
        # Implicitly add heading/trailing wildcards
        pattern = "*" + pattern + "*"
        
        for i, item in enumerate(items):
            name = getattr(item, propname, '')
            
            # This is similar to a logical xor
            if bool(name and fnmatch.fnmatch(name, pattern)) is not bool(reverse):
                flags[i] &= ~bitflag
            else:
                flags[i] = 0
        
        return flags
    
    def filter_items_in_active_regions(
        self,
        bitflag: int,
        items: List[RetargetShapesBase],
        region_dict: Dict[str, bool] = None,
        flags: List[int] = None
    ) -> List[int]:
        """
        Filter items by active regions.
        
        Args:
            bitflag: Bit flag for filtering
            items: List of items
            region_dict: Dictionary of active regions
            flags: Existing flags
            
        Returns:
            List of flags
        """
        if not region_dict or not items:
            return flags or []
        
        if flags is None:
            flags = [0] * len(items)
        
        for i, item in enumerate(items):
            region = item.region.lower()
            if region_dict.get(region, True):
                flags[i] |= bitflag
            else:
                flags[i] = 0
        
        return flags
    
    def filter_items(
        self,
        items: List[RetargetShapesBase]
    ) -> Tuple[List[int], List[int]]:
        """
        Filter and order items.
        
        Args:
            items: List of items
            
        Returns:
            Tuple of (filtered_flags, ordered_indices)
        """
        filtered = [0] * len(items)
        ordered = []
        
        # Get active regions
        face_regions = self.get_face_regions()
        active_region_dict = face_regions.get_active_regions()
        
        # Filter by active regions
        if any(active_region_dict.values()):
            filtered = self.filter_items_in_active_regions(
                self.bitflag_filter_item,
                items,
                region_dict=active_region_dict,
                flags=filtered
            )
        
        # Filter by name
        filtered = self.filter_items_by_name(
            self.filter_name,
            self.bitflag_filter_item,
            items,
            "name",
            flags=filtered,
            reverse=self.use_filter_name_reverse
        )
        
        # Sort by name
        if self.use_filter_sort_alpha:
            # Sort items by name
            sorted_items = sorted(
                [(i, item.name) for i, item in enumerate(items)],
                key=lambda x: x[1],
                reverse=self.use_filter_sort_reverse
            )
            ordered = [i for i, _ in sorted_items]
        
        return filtered, ordered


# ============================================================
# Draw Target Shapes List Base
# ============================================================

class DrawTargetShapesListBase(RetargetingBase):
    """
    Base class for drawing target shapes in a popup.
    """
    
    name = "DrawTargetShapesList"
    label = "Target Shapes"
    
    # Settings
    target_shape_edit = ''
    source_shape = ''
    edit_target_shapes_operator = ''
    target_shapes_list = ''
    use_display_name = True
    
    @classmethod
    def get_retarget_shapes(cls) -> List[RetargetShapesBase]:
        """
        Get retarget shapes from scene data.
        
        Returns:
            List of RetargetShapesBase instances
        """
        return SetDefaultRegionsBase.get_retarget_shapes()
    
    @classmethod
    def get_target_shapes_enum(cls) -> List[Tuple[str, str, str]]:
        """
        Get enum items for target shapes.
        
        Returns:
            List of (value, label, description) tuples
        """
        items = []
        faceit_objects = get_faceit_objects_list()
        
        if faceit_objects:
            shape_names = get_shape_key_names_from_objects(faceit_objects)
            for i, name in enumerate(shape_names):
                items.append((name, name, name, i))
        else:
            items.append(("None", "None", "None"))
        
        return items
    
    def draw(self, layout_func: Callable) -> None:
        """
        Draw the target shapes popup.
        
        Args:
            layout_func: Function to draw UI elements
        """
        retarget_list = self.get_retarget_shapes()
        shape_item = None
        
        # Find the shape item
        for item in retarget_list:
            if item.name == self.source_shape:
                shape_item = item
                break
        
        if not shape_item:
            layout_func("No shape found")
            return
        
        # Draw source shape name
        if self.use_display_name:
            layout_func(f"Source Shape: {shape_item.display_name}")
        else:
            layout_func(f"Source Shape: {shape_item.name}")
        
        # Draw target shapes list
        if shape_item.target_shapes:
            for ts in shape_item.target_shapes:
                layout_func(ts.name)
        else:
            layout_func("No target shapes assigned")
        
        # Draw add target shape button
        layout_func("Add Target Shape", self.edit_target_shapes_operator)
        
        # Draw invalid target shapes warning
        invalid = shape_item.get_invalid_targets()
        if invalid:
            layout_func(f"Missing Target Shapes: {', '.join(invalid)}", alert=True)
    
    def execute(self) -> bool:
        """
        Execute the operator.
        
        Returns:
            True if successful
        """
        return True


# ============================================================
# Edit Target Shape Base
# ============================================================

class EditTargetShapeBase(RetargetingBase):
    """
    Base class for editing target shapes.
    """
    
    name = "EditTargetShape"
    label = "Edit Target Shape"
    
    # Properties
    operation = 'ADD'  # 'ADD' or 'CHANGE'
    new_target_shape = ''
    source_shape_index = 0
    target_shape = ''
    
    @classmethod
    def get_retarget_shapes(cls) -> List[RetargetShapesBase]:
        """
        Get retarget shapes from scene data.
        
        Returns:
            List of RetargetShapesBase instances
        """
        return SetDefaultRegionsBase.get_retarget_shapes()
    
    @classmethod
    def save_retarget_shapes(cls, shapes: List[RetargetShapesBase]) -> bool:
        """
        Save retarget shapes to scene data.
        
        Args:
            shapes: List of RetargetShapesBase instances
            
        Returns:
            True if successful
        """
        return SetDefaultRegionsBase.save_retarget_shapes(shapes)
    
    @classmethod
    def get_target_shapes_enum(cls) -> List[Tuple[str, str, str]]:
        """
        Get enum items for target shapes.
        
        Returns:
            List of (value, label, description) tuples
        """
        return DrawTargetShapesListBase.get_target_shapes_enum()
    
    def invoke(self) -> bool:
        """
        Invoke the operator.
        
        Returns:
            True if successful
        """
        # Show search popup
        return True
    
    def execute(self) -> bool:
        """
        Execute the operator.
        
        Returns:
            True if successful
        """
        retarget_list = self.get_retarget_shapes()
        
        if self.source_shape_index >= len(retarget_list):
            return False
        
        shape_item = retarget_list[self.source_shape_index]
        
        if self.operation == 'CHANGE':
            # Change existing target shape
            for ts in shape_item.target_shapes:
                if ts.name == self.target_shape:
                    ts.name = self.new_target_shape
                    break
        else:
            # Add new target shape
            # Check if target shape is already assigned
            all_targets = []
            for item in retarget_list:
                all_targets.extend(item.get_target_shape_names())
            
            if self.new_target_shape in all_targets:
                # Find which source has this target
                source_name = ''
                for item in retarget_list:
                    if self.new_target_shape in item.get_target_shape_names():
                        source_name = item.name
                        break
                
                print(f"WARNING! The shape {self.new_target_shape} is already assigned to Source Shape {source_name}")
                return False
            
            shape_item.add_target_shape(self.new_target_shape)
        
        return self.save_retarget_shapes(retarget_list)


# ============================================================
# Remove Target Shape Base
# ============================================================

class RemoveTargetShapeBase(RetargetingBase):
    """
    Base class for removing target shapes.
    """
    
    name = "RemoveTargetShape"
    label = "Remove Target Shape"
    
    # Properties
    source_shape_index = 0
    target_shape = ''
    
    @classmethod
    def get_retarget_shapes(cls) -> List[RetargetShapesBase]:
        """
        Get retarget shapes from scene data.
        
        Returns:
            List of RetargetShapesBase instances
        """
        return SetDefaultRegionsBase.get_retarget_shapes()
    
    @classmethod
    def save_retarget_shapes(cls, shapes: List[RetargetShapesBase]) -> bool:
        """
        Save retarget shapes to scene data.
        
        Args:
            shapes: List of RetargetShapesBase instances
            
        Returns:
            True if successful
        """
        return SetDefaultRegionsBase.save_retarget_shapes(shapes)
    
    def execute(self) -> bool:
        """
        Execute the operator.
        
        Returns:
            True if successful
        """
        retarget_list = self.get_retarget_shapes()
        
        if self.source_shape_index >= len(retarget_list):
            return False
        
        shape_item = retarget_list[self.source_shape_index]
        shape_item.remove_target_shape(self.target_shape)
        
        return self.save_retarget_shapes(retarget_list)


# ============================================================
# Clear Target Shape Base
# ============================================================

class ClearTargetShapeBase(RetargetingBase):
    """
    Base class for clearing all target shapes from an item.
    """
    
    name = "ClearTargetShape"
    label = "Clear Target Shape"
    
    # Properties
    source_shape_name = ''
    
    @classmethod
    def get_retarget_shapes(cls) -> List[RetargetShapesBase]:
        """
        Get retarget shapes from scene data.
        
        Returns:
            List of RetargetShapesBase instances
        """
        return SetDefaultRegionsBase.get_retarget_shapes()
    
    @classmethod
    def save_retarget_shapes(cls, shapes: List[RetargetShapesBase]) -> bool:
        """
        Save retarget shapes to scene data.
        
        Args:
            shapes: List of RetargetShapesBase instances
            
        Returns:
            True if successful
        """
        return SetDefaultRegionsBase.save_retarget_shapes(shapes)
    
    def execute(self) -> bool:
        """
        Execute the operator.
        
        Returns:
            True if successful
        """
        retarget_list = self.get_retarget_shapes()
        
        shape_item = None
        for item in retarget_list:
            if item.name == self.source_shape_name:
                shape_item = item
                break
        
        if not shape_item:
            return False
        
        shape_item.clear_target_shapes()
        
        return self.save_retarget_shapes(retarget_list)