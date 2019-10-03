#!/bin/bash

TEST_OUTPUT_FILE=`mktemp`
STATUS=0

echo "Running test suite"
echo "------------------"
echo

python test.py tests/ideal_city.AER > "$TEST_OUTPUT_FILE"

TEMP=$?
if [ $TEMP -ne 0 ]; then
    echo "Python interpreter exited with $TEMP -- bailing out"
    exit
fi

diff "$TEST_OUTPUT_FILE" tests/ideal_city.no-parse-output.txt > /dev/null

if [ $? -ne 0 ]; then
    STATUS=$[$STATUS + 1]
    echo "no parse test -- FAILED"
else
    echo "no parse test -- PASSED"
fi

python test.py tests/ideal_city.AER 1 > "$TEST_OUTPUT_FILE"

TEMP=$?
if [ $TEMP -ne 0 ]; then
    echo "Python interpreter exited with $TEMP -- bailing out"
    exit
fi

diff "$TEST_OUTPUT_FILE" tests/ideal_city.yes-parse-output.txt > /dev/null

if [ $? -ne 0 ]; then
    STATUS=$[$STATUS + 2]
    echo "parse test    -- FAILED"
else
    echo "parse test    -- PASSED"
fi

echo
