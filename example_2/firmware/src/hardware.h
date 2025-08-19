#ifndef HARDWARE_H
#define HARDWARE_H

#include <Arduino.h>
#include "config.h"
#include "test_state.h"

// Hardware control functions
void setRelay(bool state);
void setLED(bool state);
void initializeHardware();

// Button interrupt
void IRAM_ATTR buttonISR();
extern volatile bool button_pressed;
extern volatile unsigned long last_interrupt;

#endif // HARDWARE_H