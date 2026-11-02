# Build without Gradle, using an installed Android SDK and JDK 17+.
param([Parameter(Mandatory=$true)][string]$SdkRoot)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
function Check-Exit { if ($LASTEXITCODE -ne 0) { throw "Build failed with exit code $LASTEXITCODE" } }
$androidJar = Join-Path $SdkRoot 'platforms/android-35/android.jar'
$toolsPath = Join-Path $SdkRoot 'build-tools/35.0.0'
if (!(Test-Path $androidJar) -or !(Test-Path "$toolsPath/aapt.exe")) { throw 'Install SDK platform 35 and build-tools 35.0.0 first.' }
$outPath = Join-Path $PSScriptRoot '.tools/native-build'
New-Item -ItemType Directory -Force "$outPath/classes", "$outPath/dex", "$PSScriptRoot/dist" | Out-Null
$sources = Get-ChildItem 'app/src/main/java/com/local/runsimulator/*.java' | ForEach-Object FullName
& javac -encoding UTF-8 -source 17 -target 17 -cp $androidJar -d "$outPath/classes" @sources
Check-Exit
& jar cf "$outPath/classes.jar" -C "$outPath/classes" .
Check-Exit
& "$toolsPath/d8.bat" --lib $androidJar --min-api 26 --output "$outPath/dex" "$outPath/classes.jar"
Check-Exit
# Gradle normally injects version and SDK information; add these in a temporary manifest.
[xml]$manifest = Get-Content 'app/src/main/AndroidManifest.xml' -Raw
$ns = 'http://schemas.android.com/apk/res/android'
$manifest.manifest.SetAttribute('package', 'com.local.runsimulator')
$manifest.manifest.SetAttribute('versionCode', $ns, '8') | Out-Null
$manifest.manifest.SetAttribute('versionName', $ns, '1.7') | Out-Null
$sdkNode=$manifest.CreateElement('uses-sdk')
$sdkNode.SetAttribute('minSdkVersion', $ns, '26') | Out-Null
$sdkNode.SetAttribute('targetSdkVersion', $ns, '35') | Out-Null
$manifest.manifest.PrependChild($sdkNode) | Out-Null
$manifest.Save("$outPath/AndroidManifest.xml")
& "$toolsPath/aapt.exe" package -f -M "$outPath/AndroidManifest.xml" -I $androidJar -A 'app/src/main/assets' -F "$outPath/unsigned.apk"
Check-Exit
Push-Location "$outPath/dex"
try { & "$toolsPath/aapt.exe" add "$outPath/unsigned.apk" classes.dex; Check-Exit } finally { Pop-Location }
& "$toolsPath/zipalign.exe" -f -p 4 "$outPath/unsigned.apk" "$outPath/aligned.apk"
Check-Exit
$keyPath = Join-Path $PSScriptRoot '.tools/debug.keystore'
if (!(Test-Path $keyPath)) {
    & keytool -genkeypair -keystore $keyPath -storepass android -keypass android -alias androiddebugkey -dname 'CN=Android Debug,O=Android,C=US' -keyalg RSA -keysize 2048 -validity 10000
    Check-Exit
}
& "$toolsPath/apksigner.bat" sign --ks $keyPath --ks-pass pass:android --key-pass pass:android --out "$PSScriptRoot/dist/run-simulator-debug.apk" "$outPath/aligned.apk"
Check-Exit
& "$toolsPath/apksigner.bat" verify --verbose "$PSScriptRoot/dist/run-simulator-debug.apk"
Check-Exit
Write-Host 'APK: dist/run-simulator-debug.apk'
