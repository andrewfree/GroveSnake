#!/bin/bash
MyShellVar=$(echo $1)
dialog () {
osascript <<EOD
set MyApplVar to do shell script "echo '$MyShellVar'"
tell application "Finder" to set comment of (POSIX file MyApplVar as alias) to "done"
EOD
}
dialog