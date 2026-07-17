# -*- coding: utf-8 -*-
"""
maya_faceit.install
~~~~~~~~~~~~~~~~~~~

Installation script for Maya FaceIT.

This script copies plugin files to the appropriate Maya directories
and registers the plugin with Maya.

Usage:
    python -m maya_faceit.install

Or from Maya Script Editor:
    import maya_faceit.install
    maya_faceit.install.install()
"""

import os
import sys
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_maya_user_scripts_dir() -> Path:
    """Get the Maya user scripts directory."""
    import maya.utils # type: ignore
    # This works in Maya environment
    return Path(os.environ.get("MAYA_SCRIPT_PATH", "").split(";")[0]) or Path(
        os.path.expanduser("~/Documents/maya/scripts")
    )


def get_maya_user_shelves_dir() -> Path:
    """Get the Maya user shelves directory."""
    return Path(os.environ.get("MAYA_SHELF_PATH", "").split(";")[0]) or Path(
        os.path.expanduser("~/Documents/maya/shelves")
    )


def get_maya_user_plug_ins_dir() -> Path:
    """Get the Maya user plug-ins directory."""
    return Path(os.environ.get("MAYA_PLUG_IN_PATH", "").split(";")[0]) or Path(
        os.path.expanduser("~/Documents/maya/plug-ins")
    )


def install(
    target_dir: Path = None,
    symlink: bool = False,
    copy_docs: bool = True,
    create_shelf: bool = True,
) -> bool:
    """
    Install Maya FaceIT.

    Args:
        target_dir: Target installation directory. If None, uses Maya scripts directory.
        symlink: If True, create symbolic links instead of copying.
        copy_docs: If True, copy documentation files.
        create_shelf: If True, create a shelf button for the plugin.

    Returns:
        True if installation succeeded.
    """
    if target_dir is None:
        target_dir = get_maya_user_scripts_dir()

    logger.info("Installing Maya FaceIT to %s", target_dir)

    # Create the target directory if it doesn't exist
    target_dir.mkdir(parents=True, exist_ok=True)

    # Determine source directory (the package root)
    src_dir = Path(__file__).parent

    # Copy the package
    for item in src_dir.glob("*"):
        if item.name in ["__pycache__", "install.py", "tests"]:
            continue
        dest = target_dir / item.name
        if symlink:
            try:
                if dest.exists():
                    dest.unlink()
                dest.symlink_to(item)
                logger.debug("Symlinked %s", item.name)
            except:
                logger.warning("Failed to symlink %s, copying instead", item.name)
                copy_item(item, dest)
        else:
            copy_item(item, dest)

    # Create user data directories
    user_dir = Path.home() / ".faceit"
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / "config").mkdir(exist_ok=True)
    (user_dir / "cache").mkdir(exist_ok=True)
    (user_dir / "logs").mkdir(exist_ok=True)
    (user_dir / "projects").mkdir(exist_ok=True)
    (user_dir / "temp").mkdir(exist_ok=True)

    # Copy default configuration
    config_src = src_dir / "config.json"
    config_dst = user_dir / "config" / "default.json"
    if config_src.exists():
        shutil.copy2(config_src, config_dst)

    # Create shelf button
    if create_shelf:
        create_shelf_button()

    # Update userSetup.py to load the plugin
    update_user_setup()

    logger.info("Maya FaceIT installed successfully.")
    return True


def copy_item(src: Path, dest: Path):
    """Copy a file or directory."""
    if src.is_file():
        shutil.copy2(src, dest)
    elif src.is_dir():
        shutil.copytree(src, dest, dirs_exist_ok=True)


def create_shelf_button():
    """Create a shelf button for Maya FaceIT."""
    try:
        import maya.mel as mel # type: ignore
        import maya.cmds as cmds # type: ignore
    except ImportError:
        logger.warning("Maya not available; cannot create shelf button.")
        return

    # Find the current shelf
    current_shelf = cmds.tabLayout("ShelfLayout", q=True, selectTab=True)
    if not current_shelf:
        logger.warning("No active shelf found.")
        return

    # Check if button already exists
    shelf_buttons = cmds.shelfLayout(current_shelf, q=True, childArray=True) or []
    for btn in shelf_buttons:
        if cmds.shelfButton(btn, q=True, annotation=True) == "Maya FaceIT":
            logger.info("Shelf button already exists.")
            return

    # Create the button
    cmds.shelfButton(
        parent=current_shelf,
        annotation="Maya FaceIT",
        label="FaceIT",
        image="MayaIcon.png",
        command='''
import sys
import maya_faceit
maya_faceit.show()
''',
        sourceType="python",
    )
    logger.info("Shelf button created.")


def update_user_setup():
    """Update userSetup.py to load Maya FaceIT on startup."""
    # Find userSetup.py
    scripts_dir = get_maya_user_scripts_dir()
    user_setup = scripts_dir / "userSetup.py"

    # Check if already loaded
    load_line = "import maya_faceit"
    if user_setup.exists():
        content = user_setup.read_text(encoding="utf-8")
        if "import maya_faceit" in content:
            logger.info("Maya FaceIT already in userSetup.py.")
            return

    # Append import statement
    with open(user_setup, "a", encoding="utf-8") as f:
        f.write(f"\n# Maya FaceIT Plugin\n{load_line}\n")
    logger.info("Updated userSetup.py.")


def uninstall():
    """Uninstall Maya FaceIT."""
    logger.warning("Uninstall not implemented.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    install()