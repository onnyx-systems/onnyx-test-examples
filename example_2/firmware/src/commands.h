#ifndef COMMANDS_H
#define COMMANDS_H

#include <Arduino.h>
#include "config.h"
#include "test_state.h"
#include "hardware.h"

// Command processing
void processCommand(String cmd);
void printStatus();
void printHelp();
void burnInTest(unsigned long cycles, unsigned long interval);
void printTasmotaStatus();
void printTasmotaStatus1();
void printTasmotaStatus2();
void printTasmotaStatusSTS();

#endif // COMMANDS_H