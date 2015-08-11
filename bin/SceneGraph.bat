@echo off
SETLOCAL ENABLEEXTENSIONS
SET me=%~n0
SET parent=%~dp0
echo %parent%
SET myScript=%parent%/SceneGraph
python %myScript% %*
:: pause for debugging
:: pause
