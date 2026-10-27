import os
import urllib.request
from pathlib import Path

WRAPPER_DIR = Path("gradle/wrapper")
WRAPPER_DIR.mkdir(parents=True, exist_ok=True)

PROPERTIES_FILE = WRAPPER_DIR / "gradle-wrapper.properties"
JAR_FILE = WRAPPER_DIR / "gradle-wrapper.jar"

GRADLE_VERSION = "8.12"
WRAPPER_PROPERTIES_CONTENT = f"""distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\\://services.gradle.org/distributions/gradle-{GRADLE_VERSION}-bin.zip
networkTimeout=10000
validateDistributionUrl=true
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
"""

PROPERTIES_FILE.write_text(WRAPPER_PROPERTIES_CONTENT, encoding="utf-8")

WRAPPER_JAR_URL = f"https://raw.githubusercontent.com/gradle/gradle/v{GRADLE_VERSION}.0/gradle/wrapper/gradle-wrapper.jar"
print(f"Downloading gradle-wrapper.jar from {WRAPPER_JAR_URL}...")
urllib.request.urlretrieve(WRAPPER_JAR_URL, JAR_FILE)

# Create gradlew.bat for Windows
GRADLEW_BAT = Path("gradlew.bat")
GRADLEW_BAT_CONTENT = r"""@rem
@rem Copyright 2015 the original author or authors.
@rem
@if "%DEBUG%"=="" @echo off
@rem ##########################################################################
@rem
@rem  Gradle startup script for Windows
@rem
@rem ##########################################################################

set DIRNAME=%~dp0
if "%DIRNAME%"=="" set DIRNAME=.
set APP_BASE_NAME=%~n0
set APP_HOME=%DIRNAME%

@rem Resolve Java Home
set JAVA_EXE=java.exe
%JAVA_EXE% -version >NUL 2>&1
if %ERRORLEVEL% equ 0 goto init

if defined JAVA_HOME goto findJavaFromJavaHome
echo ERROR: JAVA_HOME is not set and no 'java' command could be found in your PATH. >&2
goto fail

:findJavaFromJavaHome
set JAVA_HOME=%JAVA_HOME:"=%
set JAVA_EXE=%JAVA_HOME%/bin/java.exe
if exist "%JAVA_EXE%" goto init
echo ERROR: JAVA_HOME is set to an invalid directory: %JAVA_HOME% >&2
goto fail

:init
set CLASSPATH=%APP_HOME%\gradle\wrapper\gradle-wrapper.jar

"%JAVA_EXE%" -Dorg.gradle.appname=gradlew -classpath "%CLASSPATH%" org.gradle.wrapper.GradleWrapperMain %*
exit /b %ERRORLEVEL%

:fail
exit /b 1
"""
GRADLEW_BAT.write_text(GRADLEW_BAT_CONTENT, encoding="utf-8")

print("Bootstrap completed successfully.")
