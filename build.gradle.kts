plugins {
    java
}

group = "com.apexvanilla"
version = "1.0.0-SNAPSHOT"

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(21))
    }
}

repositories {
    mavenCentral()
}

tasks.register("initDirectories") {
    doLast {
        mkdir("patches")
        mkdir("benchmark/world-template")
        mkdir("benchmark/reports")
        mkdir("run")
    }
}

tasks.register<Exec>("applyPatches") {
    group = "patcher"
    description = "Applies all git patches from patches/ to work/Minecraft/"
    commandLine("python", "tools/patcher.py", "apply-patches")
}

tasks.register<Exec>("rebuildPatches") {
    group = "patcher"
    description = "Rebuilds git patches from work/Minecraft/ into patches/"
    commandLine("python", "tools/patcher.py", "rebuild-patches")
}

tasks.register<Exec>("buildServer") {
    group = "build"
    description = "Compiles patched server sources and packages runnable server.jar"
    commandLine("python", "tools/patcher.py", "build-jar")
}
