"""
maya_faceit.landmark.landmark_database

Central landmark database used by Maya Faceit.

Supports MediaPipe Face Mesh (468/478 landmarks)
and future landmark providers.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


# ------------------------------------------------------------
# Data Classes
# ------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class Landmark:

    index: int

    name: str

    region: str

    side: str

    mirror: int | None = None


# ------------------------------------------------------------
# Database
# ------------------------------------------------------------

class LandmarkDatabase:

    """
    Central landmark database.

    Provides fast lookup by:

    - index
    - name
    - region
    - side
    """

    def __init__(self):

        self._landmarks: dict[int, Landmark] = {}

        self._name_lookup: dict[str, int] = {}

        self.loaded = False

    # -----------------------------------------------------

    def load(

        self,

        json_file: str,

    ):

        path = Path(json_file)

        if not path.exists():

            raise FileNotFoundError(path)

        with path.open(

            "r",

            encoding="utf8",

        ) as stream:

            data = json.load(stream)

        self._landmarks.clear()

        self._name_lookup.clear()

        for item in data["landmarks"]:

            landmark = Landmark(

                index=item["index"],

                name=item["name"],

                region=item["region"],

                side=item["side"],

                mirror=item.get("mirror"),

            )

            self._landmarks[landmark.index] = landmark

            self._name_lookup[landmark.name] = landmark.index

        self.loaded = True

    # -----------------------------------------------------

    def get(

        self,

        index: int,

    ) -> Landmark | None:

        return self._landmarks.get(index)

    # -----------------------------------------------------

    def get_by_name(

        self,

        name: str,

    ) -> Landmark | None:

        index = self._name_lookup.get(name)

        if index is None:

            return None

        return self._landmarks[index]

    # -----------------------------------------------------

    def region(

        self,

        region: str,

    ) -> list[Landmark]:

        return [

            lm

            for lm in self._landmarks.values()

            if lm.region == region

        ]

    # -----------------------------------------------------

    def side(

        self,

        side: str,

    ) -> list[Landmark]:

        return [

            lm

            for lm in self._landmarks.values()

            if lm.side == side

        ]

    # -----------------------------------------------------

    def mirror(

        self,

        index: int,

    ) -> Landmark | None:

        landmark = self.get(index)

        if landmark is None:

            return None

        if landmark.mirror is None:

            return None

        return self.get(

            landmark.mirror,

        )

    # -----------------------------------------------------

    def exists(

        self,

        index: int,

    ) -> bool:

        return index in self._landmarks

    # -----------------------------------------------------

    def names(self):

        return sorted(

            self._name_lookup.keys()

        )

    # -----------------------------------------------------

    def indices(self):

        return sorted(

            self._landmarks.keys()

        )

    # -----------------------------------------------------

    def regions(self):

        return sorted({

            lm.region

            for lm in self._landmarks.values()

        })

    # -----------------------------------------------------

    def count(self):

        return len(

            self._landmarks

        )

    # -----------------------------------------------------

    def clear(self):

        self._landmarks.clear()

        self._name_lookup.clear()

        self.loaded = False


# ------------------------------------------------------------
# Singleton
# ------------------------------------------------------------

landmark_database = LandmarkDatabase()