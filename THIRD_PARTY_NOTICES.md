# Third-party notices

The mobile generator follows the documented pipeline and data model of the local `keep-data-sim-main` project. That project declares the MIT License in `keep-data-sim-main/LICENSE`; the original license text remains there. The Android implementation is an independent Java implementation and does not copy Python source code.

The generated GPX uses GPX 1.1 and the Garmin TrackPointExtension namespace. FIT output is a minimal activity encoder implemented locally; it does not bundle Garmin SDK code.

Version 1.4 optionally loads AMap's official JavaScript API 2.0 and its official standard/satellite map layers from AMap's servers. These are proprietary services subject to AMap's terms and the user's API credentials, not covered by this project's MIT reference. No AMap SDK source, map tiles or third-party keys are bundled. AMap attribution is retained in the map viewport. See https://lbs.amap.com/api/javascript-api-v2/guide/abc/prepare for credential setup.
