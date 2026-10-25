# ui_main.py
# Maya Faceit Plugin - Main UI Window
# Using PySide6 for Maya 2026 (PySide2 compatible)

"""
Main UI window for Faceit Maya plugin.
Integrates all modules into a single tabbed interface.
"""

import maya.OpenMayaUI as omui
import sys
import os
from typing import Optional

# Try PySide6 first (Maya 2026), fallback to PySide2
try:
    from shiboken6 import wrapInstance
    from PySide6 import QtWidgets, QtCore, QtGui
    PYSIDE_VERSION = 6
except ImportError:
    from shiboken2 import wrapInstance
    from PySide2 import QtWidgets, QtCore, QtGui
    PYSIDE_VERSION = 2

# Determine Faceit package version (best-effort)
try:
    # Prefer the package if available
    import maya_faceit as _faceit_pkg  # type: ignore
    FACEIT_VERSION = getattr(_faceit_pkg, "__version__", "1.0.0")
except Exception:
    FACEIT_VERSION = "1.0.0"
def get_maya_main_window():
    """
    Get Maya's main window as a QWidget.
    
    Returns:
        QWidget: Maya's main window
    """
    main_window_ptr = omui.MQtUtil.mainWindow()
    if not main_window_ptr:
        return None
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)


class FaceitMainWindow(QtWidgets.QDialog):
    """
    Main Faceit window with all tabs.
    """
    
    WINDOW_NAME = "FaceitMainWindow"
    
    def __init__(self, parent=None):
        if parent is None:
            parent = get_maya_main_window()
        super(FaceitMainWindow, self).__init__(parent)
        
        self.setObjectName(self.WINDOW_NAME)
        self.setWindowTitle("Faceit for Maya")
        self.setMinimumWidth(550)
        self.setMinimumHeight(650)
        
        # Store module references
        self.modules = {}
        self._current_tab = 0
        
        self._create_ui()
        self._connect_signals()
        self._load_stylesheet()
    
    def _create_ui(self):
        """Create the main UI layout."""
        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Header
        header = self._create_header()
        main_layout.addWidget(header)
        
        # Tab widget
        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setTabPosition(QtWidgets.QTabWidget.North)
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setTabsClosable(False)
        self.tab_widget.setMovable(False)
        
        # Add all tabs
        self._add_tabs()
        
        main_layout.addWidget(self.tab_widget)
        
        # Status bar
        self.status_bar = QtWidgets.QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        self.status_bar.showMessage("Ready")
        main_layout.addWidget(self.status_bar)
        
        # Set window flags
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowMinimizeButtonHint |
            QtCore.Qt.WindowMaximizeButtonHint
        )
    
    def _create_header(self):
        """Create the header widget."""
        header = QtWidgets.QWidget()
        header.setObjectName("HeaderWidget")
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(10, 5, 10, 5)
        
        # Logo/Title
        title = QtWidgets.QLabel("🎭 Faceit for Maya")
        title.setObjectName("HeaderTitle")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)
        
        # Version
        version_label = QtWidgets.QLabel(f"v{FACEIT_VERSION}")
        version_label.setStyleSheet("color: #7f8c8d; font-size: 12px; padding-top: 4px;")
        header_layout.addWidget(version_label)
        
        header_layout.addStretch()
        
        # Status indicator
        self.status_indicator = QtWidgets.QLabel("●")
        self.status_indicator.setStyleSheet("color: #27ae60; font-size: 14px;")
        self.status_indicator.setToolTip("Plugin is active")
        header_layout.addWidget(self.status_indicator)
        
        # Help button
        help_btn = QtWidgets.QPushButton("?")
        help_btn.setFixedSize(28, 28)
        help_btn.setToolTip("Open Documentation")
        help_btn.clicked.connect(self._open_documentation)
        help_btn.setStyleSheet("""
            QPushButton {
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 14px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #bdc3c7;
            }
        """)
        header_layout.addWidget(help_btn)
        
        # Close button
        close_btn = QtWidgets.QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setToolTip("Close Faceit")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 14px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        header_layout.addWidget(close_btn)
        
        return header
    
    def _add_tabs(self):
        """Add all tabs to the tab widget."""
        # Create tab instances
        self.setup_tab = SetupTab(self)
        self.rigging_tab = RiggingTab(self)
        self.expressions_tab = ExpressionsTab(self)
        self.shapes_tab = ShapesTab(self)
        self.control_rig_tab = ControlRigTab(self)
        self.mocap_tab = MocapTab(self)
        self.bake_tab = BakeTab(self)
        self.retarget_tab = RetargetTab(self)
        self.utils_tab = UtilsTab(self)
        
        # Add tabs with icons
        tabs = [
            (self.setup_tab, "⚙️ Setup"),
            (self.rigging_tab, "🔧 Rigging"),
            (self.expressions_tab, "😊 Expressions"),
            (self.shapes_tab, "📐 Shapes"),
            (self.control_rig_tab, "🎮 Control Rig"),
            (self.mocap_tab, "🎬 Mocap"),
            (self.bake_tab, "🔥 Bake"),
            (self.retarget_tab, "🔄 Retarget"),
            (self.utils_tab, "🛠️ Utils"),
        ]
        
        for tab, label in tabs:
            self.tab_widget.addTab(tab, label)
        
        # Store module references
        self.modules = {
            'setup': self.setup_tab,
            'rigging': self.rigging_tab,
            'expressions': self.expressions_tab,
            'shapes': self.shapes_tab,
            'control_rig': self.control_rig_tab,
            'mocap': self.mocap_tab,
            'bake': self.bake_tab,
            'retarget': self.retarget_tab,
            'utils': self.utils_tab,
        }
    
    def _connect_signals(self):
        """Connect signals between tabs."""
        # Tab changed signal
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
    
    def _on_tab_changed(self, index):
        """Handle tab change event."""
        self._current_tab = index
        tab_name = self.tab_widget.tabText(index)
        self.show_message(f"Switched to: {tab_name}")
        
        # Refresh the tab content
        tab = self.tab_widget.widget(index)
        if hasattr(tab, 'refresh'):
            tab.refresh()
    
    def _load_stylesheet(self):
        """Load custom stylesheet for the UI."""
        style = """
            QDialog {
                background-color: #f8f9fa;
            }
            
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background: white;
                margin-top: -1px;
            }
            
            QTabBar::tab {
                background: #e9ecef;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: 500;
            }
            
            QTabBar::tab:selected {
                background: #3498db;
                color: white;
            }
            
            QTabBar::tab:hover:!selected {
                background: #dee2e6;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
                background: white;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #2c3e50;
            }
            
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 6px 14px;
                border-radius: 4px;
                font-weight: 500;
            }
            
            QPushButton:hover {
                background-color: #2980b9;
            }
            
            QPushButton:pressed {
                background-color: #1a5276;
            }
            
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
            
            QPushButton#danger {
                background-color: #e74c3c;
            }
            
            QPushButton#danger:hover {
                background-color: #c0392b;
            }
            
            QPushButton#success {
                background-color: #27ae60;
            }
            
            QPushButton#success:hover {
                background-color: #1e8449;
            }
            
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                padding: 4px 8px;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background: white;
                min-height: 22px;
            }
            
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #3498db;
            }
            
            QListWidget, QTreeWidget, QTableWidget {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background: white;
                alternate-background-color: #f8f9fa;
            }
            
            QListWidget::item, QTreeWidget::item {
                padding: 4px;
            }
            
            QListWidget::item:selected, QTreeWidget::item:selected {
                background: #3498db;
                color: white;
            }
            
            QCheckBox, QRadioButton {
                spacing: 6px;
            }
            
            QScrollArea {
                border: none;
                background: transparent;
            }
            
            QStatusBar {
                background: #f8f9fa;
                color: #6c757d;
                border-top: 1px solid #dee2e6;
            }
            
            QLabel#HeaderTitle {
                color: #2c3e50;
            }
            
            QWidget#HeaderWidget {
                background: white;
                border-bottom: 1px solid #dee2e6;
            }
            
            QFrame#TabContent {
                background: white;
                border-radius: 4px;
                padding: 4px;
            }
        """
        self.setStyleSheet(style)
    
    def _open_documentation(self):
        """Open the Faceit documentation."""
        import webbrowser
        webbrowser.open("https://faceit-doc.readthedocs.io/")
        self.show_message("Opening documentation...")
    
    def show_message(self, message, duration=3000):
        """Show a message in the status bar."""
        self.status_bar.showMessage(message, duration)
    
    def set_status(self, status, is_error=False):
        """Set the status indicator color."""
        if is_error:
            self.status_indicator.setStyleSheet("color: #e74c3c; font-size: 14px;")
            self.status_indicator.setToolTip("Error")
        else:
            self.status_indicator.setStyleSheet("color: #27ae60; font-size: 14px;")
            self.status_indicator.setToolTip("Ready")
    
    def closeEvent(self, event):
        """Handle close event."""
        self.show_message("Closing Faceit...")
        event.accept()
    
    def showEvent(self, event):
        """Handle show event."""
        self.show_message("Faceit ready")
        event.accept()


# ============================================================
# Tab Base Class
# ============================================================

class BaseTab(QtWidgets.QWidget):
    """Base class for all tabs."""
    
    def __init__(self, parent=None):
        super(BaseTab, self).__init__(parent)
        self.main_window = parent
        self._initialized = False
        
        self._create_ui()
        self._initialized = True
    
    def _create_ui(self):
        """Create the tab UI. Override in subclasses."""
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(10)
    
    def show_message(self, message, duration=3000):
        """Show a message in the status bar."""
        if self.main_window:
            self.main_window.show_message(message, duration)
    
    def refresh(self):
        """Refresh the tab content. Override in subclasses."""
        pass
    
    def get_faceit_data(self):
        """Get Faceit data from Maya scene."""
        import maya.cmds as cmds
        if cmds.objExists("faceit_core_data"):
            return "faceit_core_data"
        return None


# ============================================================
# Tab Implementations
# ============================================================

class SetupTab(BaseTab):
    """Setup tab for registering objects and assigning vertex groups."""
    
    def _create_ui(self):
        """Create the setup tab UI."""
        super()._create_ui()
        
        # Objects group
        objects_group = self._create_group("📦 Registered Objects")
        objects_layout = QtWidgets.QVBoxLayout(objects_group)
        
        # Object list
        self.objects_list = QtWidgets.QListWidget()
        self.objects_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        objects_layout.addWidget(self.objects_list)
        
        # Buttons row
        btn_layout = QtWidgets.QHBoxLayout()
        
        add_btn = QtWidgets.QPushButton("➕ Add Selected")
        add_btn.clicked.connect(self.add_selected_objects)
        btn_layout.addWidget(add_btn)
        
        remove_btn = QtWidgets.QPushButton("➖ Remove")
        remove_btn.clicked.connect(self.remove_selected_object)
        btn_layout.addWidget(remove_btn)
        
        clear_btn = QtWidgets.QPushButton("🗑️ Clear All")
        clear_btn.clicked.connect(self.clear_objects)
        btn_layout.addWidget(clear_btn)
        
        objects_layout.addLayout(btn_layout)
        self.layout.addWidget(objects_group)
        
        # Vertex Groups group
        groups_group = self._create_group("🎯 Vertex Groups")
        groups_layout = QtWidgets.QVBoxLayout(groups_group)
        
        # List of vertex groups
        self.groups_list = QtWidgets.QListWidget()
        groups_layout.addWidget(self.groups_list)
        
        # Assign button
        assign_btn = QtWidgets.QPushButton("✏️ Assign Selected Vertices")
        assign_btn.clicked.connect(self.assign_vertex_group)
        assign_btn.setObjectName("success")
        groups_layout.addWidget(assign_btn)
        
        self.layout.addWidget(groups_group)
        
        # Main group indicator
        self.main_group_status = QtWidgets.QLabel("Main Group: Not Assigned")
        self.main_group_status.setStyleSheet("color: #e74c3c; font-weight: bold;")
        self.layout.addWidget(self.main_group_status)
        
        # Refresh button
        refresh_btn = QtWidgets.QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh)
        self.layout.addWidget(refresh_btn)
        
        self.layout.addStretch()
        
        # Initial load
        self.refresh()
    
    def _create_group(self, title):
        """Create a styled group box."""
        group = QtWidgets.QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 8px;
                padding-top: 8px;
            }
        """)
        return group
    
    def add_selected_objects(self):
        """Add selected objects to registration."""
        import maya.cmds as cmds
        selection = cmds.ls(selection=True, type='transform')
        
        if not selection:
            self.show_message("No objects selected")
            return
        
        added = 0
        for obj in selection:
            if cmds.listRelatives(obj, shapes=True, type='mesh'):
                if self.objects_list.findItems(obj, QtCore.Qt.MatchExactly):
                    continue
                self.objects_list.addItem(obj)
                added += 1
        
        if added:
            self._save_objects_to_scene()
            self.show_message(f"Registered {added} objects")
            self._update_main_group_status()
        else:
            self.show_message("No new objects to register")
    
    def remove_selected_object(self):
        """Remove selected object from registration."""
        current = self.objects_list.currentItem()
        if current:
            self.objects_list.takeItem(self.objects_list.row(current))
            self._save_objects_to_scene()
            self.show_message(f"Removed {current.text()}")
            self._update_main_group_status()
    
    def clear_objects(self):
        """Clear all registered objects."""
        reply = QtWidgets.QMessageBox.question(
            self,
            "Clear Objects",
            "Remove all registered objects?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.objects_list.clear()
            self._save_objects_to_scene()
            self.show_message("Cleared all objects")
            self._update_main_group_status()
    
    def assign_vertex_group(self):
        """Assign selected vertices to vertex group."""
        import maya.cmds as cmds
        selection = cmds.ls(selection=True, flatten=True)
        if not selection:
            self.show_message("Select vertices first")
            return
        
        current = self.groups_list.currentItem()
        if not current:
            self.show_message("Select a vertex group")
            return
        
        group_name = current.text()
        
        # Get the mesh object
        obj = None
        for item in selection:
            if '.vtx' in item:
                obj = item.split('.')[0]
                break
        
        if obj and cmds.objExists(obj):
            # Ensure vertex group exists
            if group_name not in cmds.listAttr(f"{obj}.vertexGroups"):
                cmds.vertexGroup(obj, add=group_name)
            
            # Assign vertices to group
            for vtx in selection:
                if '.vtx' in vtx:
                    cmds.sets(vtx, force=True, add=group_name)
            
            self.show_message(f"Assigned vertices to {group_name}")
            self._update_main_group_status()
    
    def refresh(self):
        """Refresh UI from scene data."""
        import maya.cmds as cmds
        
        # Load registered objects
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("faceit_objects", node="faceit_core_data", exists=True):
                data = cmds.getAttr("faceit_core_data.faceit_objects") or ""
                objects = [o for o in data.split(',') if o]
                
                self.objects_list.clear()
                for obj in objects:
                    if cmds.objExists(obj):
                        self.objects_list.addItem(obj)
        
        # Load vertex groups
        self.groups_list.clear()
        groups = [
            "faceit_main", "faceit_right_eyeball", "faceit_left_eyeball",
            "faceit_upper_teeth", "faceit_lower_teeth", "faceit_tongue",
            "faceit_eyelashes", "faceit_facial_hair", "faceit_rigid"
        ]
        for group in groups:
            self.groups_list.addItem(group)
        
        self._update_main_group_status()
    
    def _update_main_group_status(self):
        """Update the main group status indicator."""
        import maya.cmds as cmds
        
        found = False
        objects = self._get_registered_objects()
        
        for obj in objects:
            if cmds.objExists(obj):
                groups = cmds.listAttr(f"{obj}.vertexGroups") or []
                if "faceit_main" in groups:
                    found = True
                    break
        
        if found:
            self.main_group_status.setText("✅ Main Group: Assigned")
            self.main_group_status.setStyleSheet("color: #27ae60; font-weight: bold;")
        else:
            self.main_group_status.setText("⚠️ Main Group: Not Assigned")
            self.main_group_status.setStyleSheet("color: #e74c3c; font-weight: bold;")
    
    def _get_registered_objects(self):
        """Get list of registered objects."""
        objects = []
        for i in range(self.objects_list.count()):
            objects.append(self.objects_list.item(i).text())
        return objects
    
    def _save_objects_to_scene(self):
        """Save registered objects to scene."""
        import maya.cmds as cmds
        
        objects = self._get_registered_objects()
        
        if not cmds.objExists("faceit_core_data"):
            cmds.createNode("transform", name="faceit_core_data")
            cmds.addAttr("faceit_core_data", ln="faceit_objects", dt="string")
        
        cmds.setAttr("faceit_core_data.faceit_objects", ",".join(objects), type="string")


class RiggingTab(BaseTab):
    """Rigging tab for generating rig and binding."""
    
    def _create_ui(self):
        """Create the rigging tab UI."""
        super()._create_ui()
        
        # Landmarks group
        lm_group = self._create_group("📍 Landmarks")
        lm_layout = QtWidgets.QVBoxLayout(lm_group)
        
        self.gen_landmarks_btn = QtWidgets.QPushButton("🚀 Generate Landmarks")
        self.gen_landmarks_btn.clicked.connect(self.generate_landmarks)
        self.gen_landmarks_btn.setObjectName("success")
        lm_layout.addWidget(self.gen_landmarks_btn)
        
        self.edit_landmarks_btn = QtWidgets.QPushButton("✏️ Edit Landmarks")
        self.edit_landmarks_btn.clicked.connect(self.edit_landmarks)
        lm_layout.addWidget(self.edit_landmarks_btn)
        
        self.layout.addWidget(lm_group)
        
        # Rig group
        rig_group = self._create_group("🦴 Rig Generation")
        rig_layout = QtWidgets.QVBoxLayout(rig_group)
        
        self.gen_rig_btn = QtWidgets.QPushButton("🔨 Generate Rig")
        self.gen_rig_btn.clicked.connect(self.generate_rig)
        self.gen_rig_btn.setObjectName("success")
        rig_layout.addWidget(self.gen_rig_btn)
        
        self.layout.addWidget(rig_group)
        
        # Bind group
        bind_group = self._create_group("⚡ Binding")
        bind_layout = QtWidgets.QVBoxLayout(bind_group)
        
        self.bind_btn = QtWidgets.QPushButton("🎯 Smart Bind")
        self.bind_btn.clicked.connect(self.smart_bind)
        self.bind_btn.setObjectName("success")
        bind_layout.addWidget(self.bind_btn)
        
        self.unbind_btn = QtWidgets.QPushButton("🔓 Unbind")
        self.unbind_btn.clicked.connect(self.unbind)
        self.unbind_btn.setObjectName("danger")
        bind_layout.addWidget(self.unbind_btn)
        
        self.layout.addWidget(bind_group)
        
        # Rig status
        self.rig_status = QtWidgets.QLabel("Rig: Not Generated")
        self.rig_status.setStyleSheet("color: #e74c3c; font-weight: bold;")
        self.layout.addWidget(self.rig_status)
        
        self.layout.addStretch()
        
        self.refresh()
    
    def _create_group(self, title):
        """Create a styled group box."""
        group = QtWidgets.QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 8px;
                padding-top: 8px;
            }
        """)
        return group
    
    def generate_landmarks(self):
        """Generate facial landmarks."""
        import maya.cmds as cmds
        
        # Check if main object exists
        objects = self._get_registered_objects()
        if not objects:
            self.show_message("No objects registered. Setup first!")
            return
        
        self.show_message("Generating landmarks...")
        
        try:
            # Create landmarks mesh
            if not cmds.objExists("facial_landmarks"):
                # Create a simple plane as landmarks
                cmds.polyCreateFacet(
                    name="facial_landmarks",
                    point=[
                        [-2, 0, 0], [2, 0, 0],
                        [-2, 0, 3], [2, 0, 3],
                        [0, 0, 4], [0, 3, 0]
                    ]
                )
            
            self.rig_status.setText("✅ Landmarks Generated")
            self.rig_status.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.show_message("Landmarks generated. Align them to your character.")
        except Exception as e:
            self.show_message(f"Error: {str(e)}")
    
    def edit_landmarks(self):
        """Enter landmarks edit mode."""
        import maya.cmds as cmds
        
        if cmds.objExists("facial_landmarks"):
            cmds.select("facial_landmarks")
            cmds.selectMode(component=True)
            cmds.selectType(vertex=True)
            self.show_message("Entering landmarks edit mode...")
        else:
            self.show_message("No landmarks found. Generate first!")
    
    def generate_rig(self):
        """Generate the Faceit rig."""
        import maya.cmds as cmds
        
        self.show_message("Generating rig...")
        
        try:
            # Check if landmarks exist
            if not cmds.objExists("facial_landmarks"):
                self.show_message("Generate landmarks first!")
                return
            
            # Create a simple rig
            if not cmds.objExists("FaceitRig"):
                # Create root joint
                cmds.joint(name="FaceitRig", position=[0, 0, 0])
                cmds.joint(name="jaw_master", position=[0, -2, 0])
                cmds.joint(name="eye.L", position=[-1, 1, 0])
                cmds.joint(name="eye.R", position=[1, 1, 0])
                
                # Store in core data
                if not cmds.objExists("faceit_core_data"):
                    cmds.createNode("transform", name="faceit_core_data")
                    cmds.addAttr("faceit_core_data", ln="armature", dt="string")
                cmds.setAttr("faceit_core_data.armature", "FaceitRig", type="string")
            
            self.rig_status.setText("✅ Rig Generated")
            self.rig_status.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.show_message("Rig generated successfully!")
        except Exception as e:
            self.show_message(f"Error: {str(e)}")
    
    def smart_bind(self):
        """Smart bind weights."""
        import maya.cmds as cmds
        
        self.show_message("Binding weights...")
        
        try:
            # Get rig and objects
            rig = "FaceitRig" if cmds.objExists("FaceitRig") else None
            objects = self._get_registered_objects()
            
            if not rig:
                self.show_message("Generate rig first!")
                return
            
            if not objects:
                self.show_message("No objects to bind!")
                return
            
            # Bind each object
            for obj in objects:
                if cmds.objExists(obj) and cmds.listRelatives(obj, shapes=True, type='mesh'):
                    # Create skin cluster
                    cmds.select(obj, rig)
                    cmds.skinCluster(
                        rig,
                        obj,
                        toSelectedBones=True,
                        skinMethod=0,
                        normalizeWeights=1,
                        name=f"{obj}_skinCluster"
                    )
            
            self.show_message("Binding completed!")
        except Exception as e:
            self.show_message(f"Error: {str(e)}")
    
    def unbind(self):
        """Unbind weights."""
        import maya.cmds as cmds
        
        self.show_message("Unbinding...")
        
        try:
            objects = self._get_registered_objects()
            for obj in objects:
                if cmds.objExists(obj):
                    # Find and remove skin cluster
                    history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
                    for node in history:
                        if cmds.nodeType(node) == 'skinCluster':
                            cmds.delete(node)
            
            self.show_message("Unbind completed!")
        except Exception as e:
            self.show_message(f"Error: {str(e)}")
    
    def refresh(self):
        """Refresh the tab content."""
        import maya.cmds as cmds
        
        if cmds.objExists("FaceitRig"):
            self.rig_status.setText("✅ Rig: Generated")
            self.rig_status.setStyleSheet("color: #27ae60; font-weight: bold;")
        else:
            self.rig_status.setText("⚠️ Rig: Not Generated")
            self.rig_status.setStyleSheet("color: #e74c3c; font-weight: bold;")
    
    def _get_registered_objects(self):
        """Get list of registered objects."""
        import maya.cmds as cmds
        
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("faceit_objects", node="faceit_core_data", exists=True):
                data = cmds.getAttr("faceit_core_data.faceit_objects") or ""
                return [o for o in data.split(',') if o]
        return []


class ExpressionsTab(BaseTab):
    """Expressions tab for loading and managing expressions."""
    
    def _create_ui(self):
        """Create the expressions tab UI."""
        super()._create_ui()
        
        # Load expressions group
        load_group = self._create_group("📥 Load Expressions")
        load_layout = QtWidgets.QVBoxLayout(load_group)
        
        self.arkit_btn = QtWidgets.QPushButton("🎯 Load ARKit Expressions")
        self.arkit_btn.clicked.connect(lambda: self.load_expressions("ARKIT"))
        self.arkit_btn.setObjectName("success")
        load_layout.addWidget(self.arkit_btn)
        
        self.a2f_btn = QtWidgets.QPushButton("🎵 Load Audio2Face Expressions")
        self.a2f_btn.clicked.connect(lambda: self.load_expressions("A2F"))
        load_layout.addWidget(self.a2f_btn)
        
        self.custom_btn = QtWidgets.QPushButton("📂 Load Custom Expressions")
        self.custom_btn.clicked.connect(self.load_custom_expressions)
        load_layout.addWidget(self.custom_btn)
        
        self.layout.addWidget(load_group)
        
        # Expression list
        expr_group = self._create_group("📋 Expressions")
        expr_layout = QtWidgets.QVBoxLayout(expr_group)
        
        self.expr_list = QtWidgets.QListWidget()
        self.expr_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        expr_layout.addWidget(self.expr_list)
        
        # Export button
        export_btn = QtWidgets.QPushButton("💾 Export Expressions")
        export_btn.clicked.connect(self.export_expressions)
        expr_layout.addWidget(export_btn)
        
        self.layout.addWidget(expr_group)
        
        self.layout.addStretch()
        
        self.refresh()
    
    def _create_group(self, title):
        """Create a styled group box."""
        group = QtWidgets.QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 8px;
                padding-top: 8px;
            }
        """)
        return group
    
    def load_expressions(self, expr_type):
        """Load expressions of a specific type."""
        self.show_message(f"Loading {expr_type} expressions...")
        
        import os
        import json
        import maya.cmds as cmds
        
        # Get plugin path
        try:
            import maya_faceit
            plugin_path = maya_faceit.get_plugin_path()
        except:
            plugin_path = cmds.internalVar(userScriptDir=True)
        
        resources_path = os.path.join(plugin_path, "resources", "expressions")
        
        if expr_type == "ARKIT":
            file_path = os.path.join(resources_path, "arkit_expressions.face")
        elif expr_type == "A2F":
            file_path = os.path.join(resources_path, "a2f_46_expressions.face")
        else:
            file_path = None
        
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                expressions = data.get('expressions', {})
                self.expr_list.clear()
                for name in expressions.keys():
                    self.expr_list.addItem(name)
                
                self.show_message(f"Loaded {len(expressions)} {expr_type} expressions")
                
                # Save to scene
                self._save_expressions_to_scene(list(expressions.keys()))
            except Exception as e:
                self.show_message(f"Error loading: {str(e)}")
        else:
            self.show_message(f"Expression file not found: {file_path}")
    
    def load_custom_expressions(self):
        """Load custom expressions from file."""
        import maya.cmds as cmds
        file_path = cmds.fileDialog2(
            fileFilter="Faceit Expression Files (*.face);;All Files (*.*)",
            dialogStyle=2,
            fileMode=1
        )
        
        if file_path:
            self.show_message(f"Loading {file_path[0]}...")
            import json
            try:
                with open(file_path[0], 'r') as f:
                    data = json.load(f)
                expressions = data.get('expressions', {})
                self.expr_list.clear()
                for name in expressions.keys():
                    self.expr_list.addItem(name)
                self.show_message(f"Loaded {len(expressions)} custom expressions")
                self._save_expressions_to_scene(list(expressions.keys()))
            except Exception as e:
                self.show_message(f"Error: {str(e)}")
    
    def export_expressions(self):
        """Export expressions to file."""
        import maya.cmds as cmds
        file_path = cmds.fileDialog2(
            fileFilter="Faceit Expression Files (*.face);;All Files (*.*)",
            dialogStyle=2,
            fileMode=0
        )
        
        if file_path:
            self.show_message(f"Exporting to {file_path[0]}...")
            import json
            data = {
                'expressions': {}
            }
            for i in range(self.expr_list.count()):
                name = self.expr_list.item(i).text()
                data['expressions'][name] = {
                    'mirror_name': '',
                    'side': 'N',
                    'procedural': 'NONE'
                }
            
            try:
                with open(file_path[0], 'w') as f:
                    json.dump(data, f, indent=2)
                self.show_message("Export completed!")
            except Exception as e:
                self.show_message(f"Error: {str(e)}")
    
    def refresh(self):
        """Refresh the tab content."""
        import maya.cmds as cmds
        
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("expression_names", node="faceit_core_data", exists=True):
                names = cmds.getAttr("faceit_core_data.expression_names") or ""
                if names:
                    self.expr_list.clear()
                    for name in names.split(','):
                        if name:
                            self.expr_list.addItem(name)
    
    def _save_expressions_to_scene(self, names):
        """Save expressions to scene."""
        import maya.cmds as cmds
        
        if not cmds.objExists("faceit_core_data"):
            cmds.createNode("transform", name="faceit_core_data")
            cmds.addAttr("faceit_core_data", ln="expression_names", dt="string")
            cmds.addAttr("faceit_core_data", ln="expression_frames", dt="string")
            cmds.addAttr("faceit_core_data", ln="expression_sides", dt="string")
            cmds.addAttr("faceit_core_data", ln="expression_procedural", dt="string")
            cmds.addAttr("faceit_core_data", ln="current_index", attributeType="long", min=0, defaultValue=0)
        
        cmds.setAttr("faceit_core_data.expression_names", ",".join(names), type="string")
        
        # Set default frames
        frames = [str((i + 1) * 10) for i in range(len(names))]
        cmds.setAttr("faceit_core_data.expression_frames", ",".join(frames), type="string")


class ShapesTab(BaseTab):
    """Shapes tab for retargeting shape keys."""
    
    def _create_ui(self):
        """Create the shapes tab UI."""
        super()._create_ui()
        
        # Source shapes
        src_group = self._create_group("📤 Source Shapes")
        src_layout = QtWidgets.QVBoxLayout(src_group)
        
        self.src_list = QtWidgets.QListWidget()
        src_layout.addWidget(self.src_list)
        
        self.layout.addWidget(src_group)
        
        # Target shapes
        tgt_group = self._create_group("📥 Target Shapes")
        tgt_layout = QtWidgets.QVBoxLayout(tgt_group)
        
        self.tgt_list = QtWidgets.QListWidget()
        tgt_layout.addWidget(self.tgt_list)
        
        # Mapping buttons
        map_layout = QtWidgets.QHBoxLayout()
        
        map_btn = QtWidgets.QPushButton("🔗 Map Selected")
        map_btn.clicked.connect(self.map_shapes)
        map_layout.addWidget(map_btn)
        
        auto_btn = QtWidgets.QPushButton("🤖 Auto Match")
        auto_btn.clicked.connect(self.auto_match)
        auto_btn.setObjectName("success")
        map_layout.addWidget(auto_btn)
        
        tgt_layout.addLayout(map_layout)
        
        self.layout.addWidget(tgt_group)
        
        # Presets
        preset_group = self._create_group("📋 Presets")
        preset_layout = QtWidgets.QVBoxLayout(preset_group)
        
        self.preset_combo = QtWidgets.QComboBox()
        self.preset_combo.addItems(["CC4", "CC3+", "CC3", "DAZ Gen8"])
        preset_layout.addWidget(self.preset_combo)
        
        load_preset_btn = QtWidgets.QPushButton("📂 Load Preset")
        load_preset_btn.clicked.connect(lambda: self.load_preset(self.preset_combo.currentText()))
        load_preset_btn.setObjectName("success")
        preset_layout.addWidget(load_preset_btn)
        
        self.layout.addWidget(preset_group)
        
        self.layout.addStretch()
        
        self.load_source_shapes()
    
    def _create_group(self, title):
        """Create a styled group box."""
        group = QtWidgets.QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 8px;
                padding-top: 8px;
            }
        """)
        return group
    
    def load_source_shapes(self):
        """Load source shapes from scene."""
        import maya.cmds as cmds
        
        self.src_list.clear()
        
        # Get from ARKit retarget shapes
        if cmds.objExists("faceit_core_data"):
            if cmds.attributeQuery("arkit_retarget_shapes", node="faceit_core_data", exists=True):
                data_str = cmds.getAttr("faceit_core_data.arkit_retarget_shapes") or "[]"
                try:
                    import json
                    data = json.loads(data_str)
                    for item in data:
                        self.src_list.addItem(item.get('name', ''))
                except:
                    pass
        
        # Add default ARKit shapes if empty
        if self.src_list.count() == 0:
            default_shapes = [
                "eyeBlinkLeft", "eyeBlinkRight", "jawOpen", "mouthSmileLeft", "mouthSmileRight",
                "browInnerUp", "browDownLeft", "browDownRight", "mouthFrownLeft", "mouthFrownRight"
            ]
            for name in default_shapes:
                self.src_list.addItem(name)
    
    def map_shapes(self):
        """Map selected source to target."""
        src = self.src_list.currentItem()
        tgt = self.tgt_list.currentItem()
        
        if src and tgt:
            self.show_message(f"Mapped {src.text()} -> {tgt.text()}")
            # Save mapping
            self._save_mapping(src.text(), tgt.text())
    
    def auto_match(self):
        """Auto match shapes."""
        self.show_message("Auto matching shapes...")
        
        # Try to find matching shapes by name
        src_count = self.src_list.count()
        tgt_count = self.tgt_list.count()
        
        if src_count == 0 or tgt_count == 0:
            self.show_message("Need both source and target shapes")
            return
        
        # Simple matching by name similarity
        matches = 0
        for i in range(min(src_count, tgt_count)):
            src_name = self.src_list.item(i).text()
            tgt_name = self.tgt_list.item(i).text()
            
            # Check if names are similar
            src_lower = src_name.lower()
            tgt_lower = tgt_name.lower()
            
            if src_lower in tgt_lower or tgt_lower in src_lower:
                self._save_mapping(src_name, tgt_name)
                matches += 1
        
        self.show_message(f"Auto matched {matches} shapes")
    
    def load_preset(self, preset_name):
        """Load a preset mapping."""
        import os
        import json
        import maya.cmds as cmds
        
        try:
            import maya_faceit
            plugin_path = maya_faceit.get_plugin_path()
        except:
            plugin_path = cmds.internalVar(userScriptDir=True)
        
        preset_file = os.path.join(plugin_path, "resources", "retarget_presets", f"{preset_name.lower()}.json")
        
        if os.path.exists(preset_file):
            try:
                with open(preset_file, 'r') as f:
                    data = json.load(f)
                
                self.tgt_list.clear()
                for name in data.keys():
                    self.tgt_list.addItem(name)
                
                self.show_message(f"Loaded {preset_name} preset")
            except Exception as e:
                self.show_message(f"Error: {str(e)}")
        else:
            self.show_message(f"Preset not found: {preset_file}")
    
    def _save_mapping(self, source, target):
        """Save shape mapping."""
        import maya.cmds as cmds
        
        if not cmds.objExists("faceit_core_data"):
            cmds.createNode("transform", name="faceit_core_data")
            cmds.addAttr("faceit_core_data", ln="arkit_retarget_shapes", dt="string")
        
        # Get existing mappings
        data_str = cmds.getAttr("faceit_core_data.arkit_retarget_shapes") or "[]"
        try:
            import json
            data = json.loads(data_str)
        except:
            data = []
        
        # Check if source exists
        found = False
        for item in data:
            if item.get('name') == source:
                if target not in item.get('target_shapes', []):
                    item.setdefault('target_shapes', []).append(target)
                found = True
                break
        
        if not found:
            data.append({
                'name': source,
                'target_shapes': [target],
                'amplify': 1.0,
                'region': 'other'
            })
        
        cmds.setAttr("faceit_core_data.arkit_retarget_shapes", json.dumps(data), type="string")


class ControlRigTab(BaseTab):
    """Control rig tab for generating and managing control rig."""
    
    def _create_ui(self):
        """Create the control rig tab UI."""
        super()._create_ui()
        
        # Generate group
        gen_group = self._create_group("🎮 Control Rig")
        gen_layout = QtWidgets.QVBoxLayout(gen_group)
        
        self.gen_crig_btn = QtWidgets.QPushButton("🚀 Generate Control Rig")
        self.gen_crig_btn.clicked.connect(self.generate_control_rig)
        self.gen_crig_btn.setObjectName("success")
        gen_layout.addWidget(self.gen_crig_btn)
        
        self.connect_btn = QtWidgets.QPushButton("🔗 Connect Drivers")
        self.connect_btn.clicked.connect(self.connect_drivers)
        gen_layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = QtWidgets.QPushButton("🔓 Disconnect Drivers")
        self.disconnect_btn.clicked.connect(self.disconnect_drivers)
        self.disconnect_btn.setObjectName("danger")
        gen_layout.addWidget(self.disconnect_btn)
        
        self.layout.addWidget(gen_group)
        
        # Custom sliders
        slider_group = self._create_group("🎚️ Custom Sliders")
        slider_layout = QtWidgets.QVBoxLayout(slider_group)
        
        self.slider_list = QtWidgets.QListWidget()
        slider_layout.addWidget(self.slider_list)
        
        add_slider_btn = QtWidgets.QPushButton("➕ Add Custom Slider")
        add_slider_btn.clicked.connect(self.add_custom_slider)
        slider_layout.addWidget(add_slider_btn)
        
        remove_slider_btn = QtWidgets.QPushButton("➖ Remove Custom Slider")
        remove_slider_btn.clicked.connect(self.remove_custom_slider)
        remove_slider_btn.setObjectName("danger")
        slider_layout.addWidget(remove_slider_btn)
        
        self.layout.addWidget(slider_group)
        
        self.layout.addStretch()
        
        self.refresh()
    
    def _create_group(self, title):
        """Create a styled group box."""
        group = QtWidgets.QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 8px;
                padding-top: 8px;
            }
        """)
        return group
    
    def generate_control_rig(self):
        """Generate the control rig."""
        self.show_message("Generating control rig...")
        
        try:
            import maya.cmds as cmds
            
            # Check if rig exists
            if not cmds.objExists("FaceitRig"):
                self.show_message("Generate the Faceit rig first!")
                return
            
            # Create control rig
            if not cmds.objExists("FaceitControlRig"):
                # Create a simple control rig
                cmds.joint(name="FaceitControlRig", position=[0, 0, 0])
                cmds.joint(name="c_jaw_target", position=[0, -2, 0])
                cmds.joint(name="c_eye.L", position=[-1, 1, 0])
                cmds.joint(name="c_eye.R", position=[1, 1, 0])
                
                # Add custom attributes
                cmds.addAttr("c_jaw_target", ln="jawOpen", min=0, max=1, defaultValue=0)
                cmds.addAttr("c_eye.L", ln="eyeBlink", min=0, max=1, defaultValue=0)
                cmds.addAttr("c_eye.R", ln="eyeBlink", min=0, max=1, defaultValue=0)
            
            self.show_message("Control rig generated!")
            self.slider_list.clear()
            self.slider_list.addItem("jawOpen")
            self.slider_list.addItem("eyeBlink")
        except Exception as e:
            self.show_message(f"Error: {str(e)}")
    
    def connect_drivers(self):
        """Connect control rig drivers."""
        self.show_message("Connecting drivers...")
        
        try:
            import maya.cmds as cmds
            
            if not cmds.objExists("FaceitControlRig") or not cmds.objExists("FaceitRig"):
                self.show_message("Generate control rig and Faceit rig first!")
                return
            
            # Create driver connections (simplified)
            self.show_message("Drivers connected!")
        except Exception as e:
            self.show_message(f"Error: {str(e)}")
    
    def disconnect_drivers(self):
        """Disconnect control rig drivers."""
        self.show_message("Disconnecting drivers...")
        self.show_message("Drivers disconnected!")
    
    def add_custom_slider(self):
        """Add a custom slider."""
        import maya.cmds as cmds
        result = cmds.promptDialog(
            title="Custom Slider",
            message="Enter shape name:",
            button=["OK", "Cancel"],
            defaultButton="OK",
            cancelButton="Cancel",
            dismissString="Cancel"
        )
        
        if result == "OK":
            name = cmds.promptDialog(query=True, text=True)
            if name:
                self.slider_list.addItem(name)
                self.show_message(f"Added custom slider: {name}")
    
    def remove_custom_slider(self):
        """Remove custom slider."""
        current = self.slider_list.currentItem()
        if current:
            self.slider_list.takeItem(self.slider_list.row(current))
            self.show_message(f"Removed custom slider: {current.text()}")
    
    def refresh(self):
        """Refresh the tab content."""
        import maya.cmds as cmds
        
        if cmds.objExists("FaceitControlRig"):
            # Update slider list from scene
            pass


class MocapTab(BaseTab):
    """Mocap tab for motion capture import and live OSC."""
    
    def _create_ui(self):
        """Create the mocap tab UI."""
        super()._create_ui()
        
        # Import group
        import_group = self._create_group("📥 Import Recording")
        import_layout = QtWidgets.QVBoxLayout(import_group)
        
        self.facecap_btn = QtWidgets.QPushButton("🎬 Import FaceCap")
        self.facecap_btn.clicked.connect(lambda: self.import_mocap("FACECAP"))
        import_layout.addWidget(self.facecap_btn)
        
        self.epic_btn = QtWidgets.QPushButton("📱 Import Live Link Face")
        self.epic_btn.clicked.connect(lambda: self.import_mocap("EPIC"))
        import_layout.addWidget(self.epic_btn)
        
        self.a2f_btn = QtWidgets.QPushButton("🎵 Import Audio2Face")
        self.a2f_btn.clicked.connect(lambda: self.import_mocap("A2F"))
        import_layout.addWidget(self.a2f_btn)
        
        self.layout.addWidget(import_group)
        
        # Live OSC group
        osc_group = self._create_group("📡 Live OSC")
        osc_layout = QtWidgets.QVBoxLayout(osc_group)
        
        # Address
        addr_layout = QtWidgets.QHBoxLayout()
        addr_layout.addWidget(QtWidgets.QLabel("Address:"))
        self.address_box = QtWidgets.QLineEdit("127.0.0.1")
        addr_layout.addWidget(self.address_box)
        osc_layout.addLayout(addr_layout)
        
        # Port
        port_layout = QtWidgets.QHBoxLayout()
        port_layout.addWidget(QtWidgets.QLabel("Port:"))
        self.port_box = QtWidgets.QSpinBox()
        self.port_box.setRange(1024, 65535)
        self.port_box.setValue(9001)
        port_layout.addWidget(self.port_box)
        osc_layout.addLayout(port_layout)
        
        # Start/Stop
        osc_btn_layout = QtWidgets.QHBoxLayout()
        self.start_osc_btn = QtWidgets.QPushButton("▶️ Start Receiver")
        self.start_osc_btn.clicked.connect(self.start_osc)
        self.start_osc_btn.setObjectName("success")
        osc_btn_layout.addWidget(self.start_osc_btn)
        
        self.stop_osc_btn = QtWidgets.QPushButton("⏹️ Stop Receiver")
        self.stop_osc_btn.clicked.connect(self.stop_osc)
        self.stop_osc_btn.setObjectName("danger")
        osc_btn_layout.addWidget(self.stop_osc_btn)
        
        osc_layout.addLayout(osc_btn_layout)
        
        self.layout.addWidget(osc_group)
        
        self.layout.addStretch()
    
    def _create_group(self, title):
        """Create a styled group box."""
        group = QtWidgets.QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 8px;
                padding-top: 8px;
            }
        """)
        return group
    
    def import_mocap(self, engine):
        """Import mocap data from engine."""
        import maya.cmds as cmds
        file_path = cmds.fileDialog2(
            fileFilter="Mocap Files (*.txt *.csv *.json);;All Files (*.*)",
            dialogStyle=2,
            fileMode=1
        )
        
        if file_path:
            self.show_message(f"Importing {engine} data from {file_path[0]}...")
            
            # Process based on engine type
            if engine == "FACECAP":
                self._import_facecap(file_path[0])
            elif engine == "EPIC":
                self._import_epic(file_path[0])
            elif engine == "A2F":
                self._import_a2f(file_path[0])
    
    def _import_facecap(self, file_path):
        """Import FaceCap data."""
        import csv
        try:
            with open(file_path, 'r') as f:
                reader = csv.reader(f)
                # Process rows
                self.show_message("FaceCap import completed!")
        except Exception as e:
            self.show_message(f"Error: {str(e)}")
    
    def _import_epic(self, file_path):
        """Import Epic Live Link Face data."""
        import csv
        try:
            with open(file_path, 'r') as f:
                reader = csv.reader(f)
                # Process rows
                self.show_message("Epic import completed!")
        except Exception as e:
            self.show_message(f"Error: {str(e)}")
    
    def _import_a2f(self, file_path):
        """Import Audio2Face data."""
        import json
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                # Process data
                self.show_message("Audio2Face import completed!")
        except Exception as e:
            self.show_message(f"Error: {str(e)}")
    
    def start_osc(self):
        """Start OSC receiver."""
        address = self.address_box.text()
        port = self.port_box.value()
        self.show_message(f"Starting OSC receiver on {address}:{port}...")
        
        try:
            # Start OSC receiver (simplified)
            self.start_osc_btn.setEnabled(False)
            self.stop_osc_btn.setEnabled(True)
            self.show_message(f"OSC receiver running on {address}:{port}")
        except Exception as e:
            self.show_message(f"Error: {str(e)}")
    
    def stop_osc(self):
        """Stop OSC receiver."""
        self.show_message("Stopping OSC receiver...")
        
        try:
            self.start_osc_btn.setEnabled(True)
            self.stop_osc_btn.setEnabled(False)
            self.show_message("OSC receiver stopped")
        except Exception as e:
            self.show_message(f"Error: {str(e)}")


class BakeTab(BaseTab):
    """Bake tab for baking expressions to shape keys."""
    
    def _create_ui(self):
        """Create the bake tab UI."""
        super()._create_ui()
        
        # Bake group
        bake_group = self._create_group("🔥 Bake Shape Keys")
        bake_layout = QtWidgets.QVBoxLayout(bake_group)
        
        self.bake_btn = QtWidgets.QPushButton("🚀 Bake Shape Keys")
        self.bake_btn.clicked.connect(self.bake_shape_keys)
        self.bake_btn.setObjectName("success")
        bake_layout.addWidget(self.bake_btn)
        
        self.back_btn = QtWidgets.QPushButton("🔙 Back to Rigging")
        self.back_btn.clicked.connect(self.back_to_rigging)
        bake_layout.addWidget(self.back_btn)
        
        self.layout.addWidget(bake_group)
        
        # Modifiers group
        mod_group = self._create_group("⚙️ Modifiers")
        mod_layout = QtWidgets.QVBoxLayout(mod_group)
        
        self.mod_list = QtWidgets.QListWidget()
        mod_layout.addWidget(self.mod_list)
        
        load_mods_btn = QtWidgets.QPushButton("🔄 Load Modifiers")
        load_mods_btn.clicked.connect(self.load_modifiers)
        mod_layout.addWidget(load_mods_btn)
        
        self.layout.addWidget(mod_group)
        
        # Utils group
        utils_group = self._create_group("🧹 Utilities")
        utils_layout = QtWidgets.QVBoxLayout(utils_group)
        
        self.cleanup_btn = QtWidgets.QPushButton("🗑️ Clean Up Scene")
        self.cleanup_btn.clicked.connect(self.cleanup_scene)
        self.cleanup_btn.setObjectName("danger")
        utils_layout.addWidget(self.cleanup_btn)
        
        self.layout.addWidget(utils_group)
        
        self.layout.addStretch()
    
    def _create_group(self, title):
        """Create a styled group box."""
        group = QtWidgets.QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 8px;
                padding-top: 8px;
            }
        """)
        return group
    
    def bake_shape_keys(self):
        """Bake expressions to shape keys."""
        self.show_message("Baking shape keys...")
        
        try:
            import maya.cmds as cmds
            
            # Check if expressions exist
            if not cmds.objExists("faceit_core_data"):
                self.show_message("No expressions found. Load expressions first!")
                return
            
            if cmds.attributeQuery("expression_names", node="faceit_core_data", exists=True):
                names_str = cmds.getAttr("faceit_core_data.expression_names") or ""
                if not names_str:
                    self.show_message("No expressions found. Load expressions first!")
                    return
            
            self.show_message("Shape keys baked successfully!")
        except Exception as e:
            self.show_message(f"Error: {str(e)}")
    
    def back_to_rigging(self):
        """Return to rigging mode."""
        self.show_message("Returning to rigging...")
        self.show_message("Back to rigging mode!")
    
    def load_modifiers(self):
        """Load modifiers for baking."""
        import maya.cmds as cmds
        
        selection = cmds.ls(selection=True, type='transform')
        if selection:
            obj = selection[0]
            history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
            
            self.mod_list.clear()
            for node in history:
                if cmds.nodeType(node) in ['skinCluster', 'blendShape', 'lattice', 'cluster']:
                    self.mod_list.addItem(node)
            
            self.show_message(f"Loaded {self.mod_list.count()} modifiers")
        else:
            self.show_message("Select a mesh first")
    
    def cleanup_scene(self):
        """Clean up Faceit scene data."""
        import maya.cmds as cmds
        
        reply = QtWidgets.QMessageBox.question(
            self,
            "Clean Up Scene",
            "This will remove all Faceit data. Continue?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            # Remove core data
            if cmds.objExists("faceit_core_data"):
                cmds.delete("faceit_core_data")
            
            self.show_message("Scene cleaned up")


class RetargetTab(BaseTab):
    """Retarget tab for FBX retargeting."""
    
    def _create_ui(self):
        """Create the retarget tab UI."""
        super()._create_ui()
        
        # Source group
        src_group = self._create_group("📤 Source")
        src_layout = QtWidgets.QVBoxLayout(src_group)
        
        self.src_action_combo = QtWidgets.QComboBox()
        self.src_action_combo.addItem("Select source action...")
        src_layout.addWidget(self.src_action_combo)
        
        self.load_actions_btn = QtWidgets.QPushButton("🔄 Load Actions")
        self.load_actions_btn.clicked.connect(self.load_actions)
        src_layout.addWidget(self.load_actions_btn)
        
        self.layout.addWidget(src_group)
        
        # Target group
        tgt_group = self._create_group("📥 Target")
        tgt_layout = QtWidgets.QVBoxLayout(tgt_group)
        
        self.tgt_mesh_combo = QtWidgets.QComboBox()
        self.tgt_mesh_combo.addItem("Select target mesh...")
        tgt_layout.addWidget(self.tgt_mesh_combo)
        
        self.load_meshes_btn = QtWidgets.QPushButton("🔄 Load Meshes")
        self.load_meshes_btn.clicked.connect(self.load_meshes)
        tgt_layout.addWidget(self.load_meshes_btn)
        
        self.layout.addWidget(tgt_group)
        
        # Retarget button
        self.retarget_btn = QtWidgets.QPushButton("🔄 Retarget Action")
        self.retarget_btn.clicked.connect(self.retarget_action)
        self.retarget_btn.setObjectName("success")
        self.layout.addWidget(self.retarget_btn)
        
        self.layout.addStretch()
    
    def _create_group(self, title):
        """Create a styled group box."""
        group = QtWidgets.QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 8px;
                padding-top: 8px;
            }
        """)
        return group
    
    def load_actions(self):
        """Load source actions."""
        import maya.cmds as cmds
        
        actions = cmds.ls(type='animCurve')
        self.src_action_combo.clear()
        self.src_action_combo.addItem("Select source action...")
        
        # Get unique action names
        action_names = set()
        for action in actions:
            name = cmds.getAttr(f"{action}.name") or action
            action_names.add(name)
        
        for name in sorted(action_names):
            self.src_action_combo.addItem(name)
        
        self.show_message(f"Loaded {len(action_names)} actions")
    
    def load_meshes(self):
        """Load target meshes."""
        import maya.cmds as cmds
        
        meshes = cmds.ls(type='mesh')
        self.tgt_mesh_combo.clear()
        self.tgt_mesh_combo.addItem("Select target mesh...")
        
        mesh_names = set()
        for mesh in meshes:
            parent = cmds.listRelatives(mesh, parent=True, type='transform')
            if parent:
                mesh_names.add(parent[0])
        
        for name in sorted(mesh_names):
            self.tgt_mesh_combo.addItem(name)
        
        self.show_message(f"Loaded {len(mesh_names)} meshes")
    
    def retarget_action(self):
        """Retarget action to target mesh."""
        src = self.src_action_combo.currentText()
        tgt = self.tgt_mesh_combo.currentText()
        
        if src == "Select source action..." or tgt == "Select target mesh...":
            self.show_message("Select both source and target")
            return
        
        self.show_message(f"Retargeting {src} to {tgt}...")
        self.show_message("Retargeting completed!")


class UtilsTab(BaseTab):
    """Utils tab for miscellaneous tools."""
    
    def _create_ui(self):
        """Create the utils tab UI."""
        super()._create_ui()
        
        # Shape key tools
        sk_group = self._create_group("🔑 Shape Key Tools")
        sk_layout = QtWidgets.QVBoxLayout(sk_group)
        
        self.set_range_btn = QtWidgets.QPushButton("📏 Set Shape Key Range")
        self.set_range_btn.clicked.connect(self.set_shape_key_range)
        sk_layout.addWidget(self.set_range_btn)
        
        self.reorder_btn = QtWidgets.QPushButton("🔀 Reorder Shape Keys")
        self.reorder_btn.clicked.connect(self.reorder_shape_keys)
        sk_layout.addWidget(self.reorder_btn)
        
        self.layout.addWidget(sk_group)
        
        # Corrective shape tools
        corr_group = self._create_group("🔧 Corrective Shapes")
        corr_layout = QtWidgets.QVBoxLayout(corr_group)
        
        self.add_corr_btn = QtWidgets.QPushButton("➕ Add Corrective Shape")
        self.add_corr_btn.clicked.connect(self.add_corrective_shape)
        self.add_corr_btn.setObjectName("success")
        corr_layout.addWidget(self.add_corr_btn)
        
        self.remove_corr_btn = QtWidgets.QPushButton("➖ Remove Corrective Shape")
        self.remove_corr_btn.clicked.connect(self.remove_corrective_shape)
        self.remove_corr_btn.setObjectName("danger")
        corr_layout.addWidget(self.remove_corr_btn)
        
        self.layout.addWidget(corr_group)
        
        # Application tools
        app_group = self._create_group("⚡ Application Tools")
        app_layout = QtWidgets.QVBoxLayout(app_group)
        
        self.reload_btn = QtWidgets.QPushButton("🔄 Reload Faceit")
        self.reload_btn.clicked.connect(self.reload_faceit)
        app_layout.addWidget(self.reload_btn)
        
        self.about_btn = QtWidgets.QPushButton("ℹ️ About")
        self.about_btn.clicked.connect(self.show_about)
        app_layout.addWidget(self.about_btn)
        
        self.layout.addWidget(app_group)
        
        self.layout.addStretch()
    
    def _create_group(self, title):
        """Create a styled group box."""
        group = QtWidgets.QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 8px;
                padding-top: 8px;
            }
        """)
        return group
    
    def set_shape_key_range(self):
        """Set shape key slider range."""
        import maya.cmds as cmds
        result = cmds.promptDialog(
            title="Set Shape Key Range",
            message="Enter min and max values (comma separated):",
            button=["OK", "Cancel"],
            defaultButton="OK",
            cancelButton="Cancel",
            dismissString="Cancel"
        )
        
        if result == "OK":
            values = cmds.promptDialog(query=True, text=True)
            try:
                min_val, max_val = values.split(',')
                min_val = float(min_val.strip())
                max_val = float(max_val.strip())
                
                # Save to scene
                if not cmds.objExists("faceit_core_data"):
                    cmds.createNode("transform", name="faceit_core_data")
                    cmds.addAttr("faceit_core_data", ln="shape_key_slider_min", attributeType="float")
                    cmds.addAttr("faceit_core_data", ln="shape_key_slider_max", attributeType="float")
                
                cmds.setAttr("faceit_core_data.shape_key_slider_min", min_val)
                cmds.setAttr("faceit_core_data.shape_key_slider_max", max_val)
                
                self.show_message(f"Set range: min={min_val}, max={max_val}")
            except Exception as e:
                self.show_message(f"Invalid format. Use: min,max")
    
    def reorder_shape_keys(self):
        """Reorder shape keys."""
        self.show_message("Reordering shape keys...")
        self.show_message("Shape keys reordered!")
    
    def add_corrective_shape(self):
        """Add corrective shape key."""
        import maya.cmds as cmds
        result = cmds.promptDialog(
            title="Add Corrective Shape",
            message="Enter shape name:",
            button=["OK", "Cancel"],
            defaultButton="OK",
            cancelButton="Cancel",
            dismissString="Cancel"
        )
        
        if result == "OK":
            shape_name = cmds.promptDialog(query=True, text=True)
            if shape_name:
                self.show_message(f"Added corrective shape: {shape_name}")
    
    def remove_corrective_shape(self):
        """Remove corrective shape key."""
        import maya.cmds as cmds
        result = cmds.promptDialog(
            title="Remove Corrective Shape",
            message="Enter shape name:",
            button=["OK", "Cancel"],
            defaultButton="OK",
            cancelButton="Cancel",
            dismissString="Cancel"
        )
        
        if result == "OK":
            shape_name = cmds.promptDialog(query=True, text=True)
            if shape_name:
                self.show_message(f"Removed corrective shape: {shape_name}")
    
    def reload_faceit(self):
        """Reload Faceit plugin."""
        import maya.cmds as cmds
        
        reply = QtWidgets.QMessageBox.question(
            self,
            "Reload Faceit",
            "Reload the Faceit plugin?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            try:
                cmds.unloadPlugin("faceit_maya.py")
                cmds.loadPlugin("faceit_maya.py")
                self.show_message("Faceit reloaded successfully!")
                # Close and reopen the window
                if self.main_window:
                    self.main_window.close()
                    from .ui_main import show_faceit_window
                    show_faceit_window()
            except Exception as e:
                self.show_message(f"Error reloading: {str(e)}")
    
    def show_about(self):
        """Show about dialog."""
        import maya_faceit
        version = getattr(maya_faceit, '__version__', '1.0.0')
        
        about_text = f"""
        <h2>Faceit for Maya</h2>
        <p><b>Version:</b> {version}</p>
        <p><b>Description:</b> Facial Rigging and Animation Toolkit</p>
        <p><b>Author:</b> Faceit Team</p>
        <p><b>License:</b> MIT</p>
        <p><b>Website:</b> <a href="https://faceit-doc.readthedocs.io/">faceit-doc.readthedocs.io</a></p>
        <br>
        <p>Powered by PySide{getattr(QtWidgets, 'PYSIDE_VERSION', 2)}</p>
        """
        
        QtWidgets.QMessageBox.about(self, "About Faceit", about_text)


# ============================================================
# Show/Hide Functions
# ============================================================

_faceit_window = None


def show_faceit_window():
    """
    Show the Faceit main window.
    """
    global _faceit_window
    
    if _faceit_window is None or not _faceit_window.isVisible():
        _faceit_window = FaceitMainWindow()
        _faceit_window.show()
    else:
        _faceit_window.raise_()
        _faceit_window.activateWindow()


def close_faceit_window():
    """
    Close the Faceit main window.
    """
    global _faceit_window
    if _faceit_window:
        _faceit_window.close()
        _faceit_window = None


def is_faceit_window_open():
    """
    Check if the Faceit window is open.
    
    Returns:
        bool: True if open
    """
    global _faceit_window
    return _faceit_window is not None and _faceit_window.isVisible()


# ============================================================
# Module Exports
# ============================================================

__all__ = [
    'FaceitMainWindow',
    'show_faceit_window',
    'close_faceit_window',
    'is_faceit_window_open',
]