# Third-party notices

The Android GPX / FIT generator is an independent Java implementation. Its generation pipeline and data model were informed by the public **keep-data-sim** project, which is distributed under the MIT License (Copyright (c) 2026 Keep Data Simulator contributors). No Python source code or runtime is included in this repository. The original MIT license text is retained in [LICENSES/keep-data-sim-MIT.txt](LICENSES/keep-data-sim-MIT.txt).

GPX output uses GPX 1.1 and the Garmin TrackPointExtension namespace. FIT output is a minimal activity encoder implemented locally; it does not bundle Garmin SDK code.

The map editor optionally loads AMap's official JavaScript API 2.0 and its official standard / satellite map layers from AMap's servers. These are proprietary services subject to AMap's terms and the user's API credentials. No AMap SDK source, map tiles or third-party keys are bundled. AMap attribution is retained in the map viewport. See https://lbs.amap.com/api/javascript-api-v2/guide/abc/prepare for credential setup.
