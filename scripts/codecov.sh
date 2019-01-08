#!/bin/bash

lcov --directory . --capture --output-file coverage.info
lcov --remove coverage.info '/usr/*' --output-file coverage.info
lcov --remove coverage.info '**/json.hpp' --output-file coverage.info

bash <(curl -s https://codecov.io/bash) -t a5bb41cf-5d71-4d3f-a310-19d3356e448b -R .. -s . -X gcov || echo "Codecov did not collect coverage reports"
