#!/bin/bash

fswatch *.py | xargs -I {} scripts/run-tests.sh

