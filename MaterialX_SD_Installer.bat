@echo off
echo -- This is in oder to install to materialX with Substance designer more easily for artist.
echo -- leegoonz.blog
echo %username%
pushd "%~dp0"
echo %~dp0sdmatxplugin
:init
IF exist "C:\Users\%username%\Documents\Allegorithmic\Substance Designer\python\sduserplugins\sdmatxplugin" (
	echo file has already exist
	rem SETX MATERIALX_ROOT "C:\Users\%username%\Documents\Allegorithmic\Substance Designer\python\sduserplugins\sdmatxplugin\MaterialX"
	SETX MATERIALX_ROOT "C:\Users\%username%\Documents\Allegorithmic\Substance Designer\python\sduserplugins\sdmatxplugin\MaterialX" /m
	goto :copydata
	) ELSE (
	echo .
	echo In now make required Substance degigner plugin directory.
	goto :makediretory
	)
:makediretory
echo ***
cd /d "C:\Users\%username%\Documents\Allegorithmic\Substance Designer\python\sduserplugins"
mkdir sdmatxplugin
echo ****
goto :init

:copydata
echo .
echo .
xcopy /d "%~dp0sdmatxplugin" "C:\Users\%username%\Documents\Allegorithmic\Substance Designer\python\sduserplugins\sdmatxplugin" /e /y /f
cd /d "C:\Users\%username%\Documents\Allegorithmic\Substance Designer\python\sduserplugins\sdmatxplugin"
dir %cd%
pause nul
