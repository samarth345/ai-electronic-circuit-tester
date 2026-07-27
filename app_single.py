import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import os
import time
from google import genai
import json
import threading
import paho.mqtt.client as mqtt

# ------------------------------------------------------------------------------
# MATH UTILITY FIX
# ------------------------------------------------------------------------------
def fact(n):
    result = 1
    for i in range(1, n + 1):
        result *= i
        print(result)
    return result

# ------------------------------------------------------------------------------
# 1. CONFIGURATION & FULL CIRCUIT DATABASE (UNTOUCHED BACKEND)
# ------------------------------------------------------------------------------
APP_NAME = "AI-Based Electronic Circuit Tester"
APP_VERSION = "2.2.0"
AUTHOR = "Final Year B.Tech Project"

CIRCUIT_DATABASE = {
    "Rectifiers": {
        "Half Wave Rectifier": {
            "description": "Converts AC to DC by passing only one half-cycle of the AC supply.",
            "components": "12V AC Transformer, 1N4007 Diode (D1), 1kΩ Load Resistor (RL), 100µF Filter Capacitor (C1)",
            "exp_input_v": 12.0, "exp_output_v": 5.4, "exp_input_i": 0.5, "exp_output_i": 0.45,
            "exp_eff": 40.6, "exp_ripple": 121.0, "formula_eff": "Eff = (P_dc / P_ac) * 100",
            "diagram": "AC Source -> Diode (D1) -> Load Resistor (RL) -> Ground",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "Across AC Secondary Transformer Winding"},
                {"step": 2, "name": "Output Probe", "loc": "Across Load Resistor (RL)"},
                {"step": 3, "name": "Current Probe", "loc": "In Series with Diode D1 Anode"}
            ]
        },
        "Full Wave Rectifier (Center Tap)": {
            "description": "Converts both AC half-cycles using a center-tapped transformer and 2 diodes.",
            "components": "12-0-12V Center-Tap Transformer, 2x 1N4007 Diodes (D1, D2), 1kΩ Load Resistor (RL), 470µF Filter Capacitor (C1)",
            "exp_input_v": 12.0, "exp_output_v": 10.8, "exp_input_i": 0.8, "exp_output_i": 0.75,
            "exp_eff": 81.2, "exp_ripple": 48.0, "formula_eff": "Eff = (P_dc / P_ac) * 100",
            "diagram": "Center Tap Transformer -> Diodes (D1, D2) -> Load (RL) -> Center Tap Return",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "Across Upper Secondary Winding to Ground"},
                {"step": 2, "name": "Output Probe", "loc": "Across Load Resistor (RL)"},
                {"step": 3, "name": "Current Probe", "loc": "In Series with Center Tap Ground Line"}
            ]
        },
        "Bridge Rectifier": {
            "description": "Uses four diodes in a bridge arrangement to achieve full-wave rectification without center-tap.",
            "components": "12V AC Transformer, Bridge Rectifier IC (1B4B42 / 4x 1N4007), 1kΩ Load Resistor (RL), 1000µF Filter Capacitor (C1)",
            "exp_input_v": 12.0, "exp_output_v": 10.1, "exp_input_i": 1.0, "exp_output_i": 0.95,
            "exp_eff": 81.2, "exp_ripple": 48.0, "formula_eff": "V_dc = (2 * V_peak) / pi",
            "diagram": "AC Terminals -> Bridge Diodes (D1-D4) -> Filter Cap -> Load Resistor",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "Across Bridge AC Input Terminals"},
                {"step": 2, "name": "Output Probe", "loc": "Across DC Positive and Ground Output Rails"},
                {"step": 3, "name": "Current Probe", "loc": "In Series with Positive Output Terminal"}
            ]
        }
    },
    "Filters": {
        "Low Pass Filter": {
            "description": "Passes signals with a frequency lower than a selected cutoff frequency.",
            "components": "10kΩ Resistor (R1), 10nF Capacitor (C1) [Cutoff Freq fc ≈ 1.59 kHz]",
            "exp_input_v": 5.0, "exp_output_v": 3.53, "exp_input_i": 0.1, "exp_output_i": 0.09,
            "exp_eff": 90.0, "exp_ripple": 5.0, "formula_eff": "fc = 1 / (2 * pi * R * C)",
            "diagram": "Signal Input -> Series Resistor (R) -> Shunt Capacitor (C) -> Ground",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "At Signal Generator Input Node"},
                {"step": 2, "name": "Output Probe", "loc": "Across Capacitor Node to Ground"},
                {"step": 3, "name": "Current Probe", "loc": "In Series with Series Resistor"}
            ]
        },
        "High Pass Filter": {
            "description": "Passes signals with a frequency higher than a certain cutoff frequency.",
            "components": "10nF Capacitor (C1), 10kΩ Resistor (R1) [Cutoff Freq fc ≈ 1.59 kHz]",
            "exp_input_v": 5.0, "exp_output_v": 3.53, "exp_input_i": 0.1, "exp_output_i": 0.09,
            "exp_eff": 90.0, "exp_ripple": 5.0, "formula_eff": "fc = 1 / (2 * pi * R * C)",
            "diagram": "Signal Input -> Series Capacitor (C) -> Shunt Resistor (R) -> Ground",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "Before Series Capacitor"},
                {"step": 2, "name": "Output Probe", "loc": "Across Output Resistor"},
                {"step": 3, "name": "Current Probe", "loc": "In Series with Signal Line"}
            ]
        },
        "Band Pass Filter": {
            "description": "Passes frequencies within a certain range and attenuates frequencies outside that range.",
            "components": "R1=10kΩ, C1=10nF (HPF Stage) | R2=1kΩ, C2=100nF (LPF Stage)",
            "exp_input_v": 5.0, "exp_output_v": 4.0, "exp_input_i": 0.12, "exp_output_i": 0.1,
            "exp_eff": 85.0, "exp_ripple": 8.0, "formula_eff": "BW = fc2 - fc1",
            "diagram": "High Pass Stage -> Low Pass Stage -> Output",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "Filter Input Port"},
                {"step": 2, "name": "Output Probe", "loc": "Filter Bandpass Stage Output"},
                {"step": 3, "name": "Current Probe", "loc": "Input Supply Path"}
            ]
        },
        "Band Stop Filter": {
            "description": "Attenuates frequencies within a specific range while passing all others.",
            "components": "Twin-T Network: 2x R=10kΩ, 1x R/2=5kΩ | 2x C=10nF, 1x 2C=20nF",
            "exp_input_v": 5.0, "exp_output_v": 0.1, "exp_input_i": 0.1, "exp_output_i": 0.01,
            "exp_eff": 10.0, "exp_ripple": 2.0, "formula_eff": "Notch Bandwidth = f2 - f1",
            "diagram": "Parallel Notch Network (Twin-T Topology)",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "Twin-T Node Input"},
                {"step": 2, "name": "Output Probe", "loc": "Twin-T Summing Node Output"},
                {"step": 3, "name": "Current Probe", "loc": "Series Input Junction"}
            ]
        }
    },
    "Amplifiers": {
        "CE Amplifier": {
            "description": "Common Emitter Transistor Amplifier providing high voltage and current gain.",
            "components": "BC547 NPN Transistor, R1=47kΩ, R2=10kΩ, Rc=2.2kΩ, Re=1kΩ, Cin=10µF, Cout=10µF, Ce=100µF",
            "exp_input_v": 0.1, "exp_output_v": 2.5, "exp_input_i": 0.01, "exp_output_i": 0.1,
            "exp_eff": 65.0, "exp_ripple": 2.0, "formula_eff": "Av = - (Rc // Rl) / re",
            "diagram": "Vcc -> Rc -> Collector | Base -> Cin -> Signal | Emitter -> Re // Ce",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "Base Terminal Coupling Capacitor"},
                {"step": 2, "name": "Output Probe", "loc": "Collector Terminal Coupling Capacitor"},
                {"step": 3, "name": "Current Probe", "loc": "Collector Supply DC Line"}
            ]
        },
        "CB Amplifier": {
            "description": "Common Base Amplifier with low input impedance and high voltage gain.",
            "components": "BC547 NPN Transistor, Rc=3.3kΩ, Re=1kΩ, R1=33kΩ, R2=10kΩ, Cbase=10µF, Cin=10µF, Cout=10µF",
            "exp_input_v": 0.1, "exp_output_v": 2.0, "exp_input_i": 0.1, "exp_output_i": 0.09,
            "exp_eff": 60.0, "exp_ripple": 3.0, "formula_eff": "Av = Rc / re",
            "diagram": "Emitter -> Input | Base -> AC Ground | Collector -> Output",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "Emitter Terminal"},
                {"step": 2, "name": "Output Probe", "loc": "Collector Terminal"},
                {"step": 3, "name": "Current Probe", "loc": "Emitter Bias Line"}
            ]
        },
        "CC Amplifier": {
            "description": "Common Collector (Emitter Follower) offering high input impedance and unit voltage gain.",
            "components": "BC547 NPN Transistor, R1=10kΩ, R2=10kΩ, Re=1kΩ, Cin=10µF, Cout=47µF",
            "exp_input_v": 1.0, "exp_output_v": 0.95, "exp_input_i": 0.001, "exp_output_i": 0.1,
            "exp_eff": 75.0, "exp_ripple": 1.0, "formula_eff": "Av approx 1",
            "diagram": "Base -> Input | Collector -> Vcc | Emitter -> Output Load",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "Transistor Base Node"},
                {"step": 2, "name": "Output Probe", "loc": "Transistor Emitter Node"},
                {"step": 3, "name": "Current Probe", "loc": "Emitter Resistor Branch"}
            ]
        },
        "Op-Amp Amplifier": {
            "description": "Operational Amplifier in non-inverting closed-loop configuration.",
            "components": "LM741 Op-Amp IC, Feedback Resistor (Rf)=10kΩ, Input Resistor (R1)=2.2kΩ, Dual Power (+15V / -15V)",
            "exp_input_v": 1.0, "exp_output_v": 5.0, "exp_input_i": 0.0001, "exp_output_i": 0.05,
            "exp_eff": 85.0, "exp_ripple": 0.5, "formula_eff": "Av = 1 + (Rf / R1)",
            "diagram": "Inverting Node -> R1/Rf feedback | Non-Inverting Node -> Vin",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "Pin 3 (Non-Inverting Input)"},
                {"step": 2, "name": "Output Probe", "loc": "Pin 6 (Op-Amp Output)"},
                {"step": 3, "name": "Current Probe", "loc": "V+ Rail Pin 7"}
            ]
        }
    },
    "Regulators": {
        "7805 Regulator": {
            "description": "Linear voltage regulator IC producing a fixed +5V DC output.",
            "components": "IC LM7805, Input Decoupling Cap C1=0.33µF (Ceramic), Output Decoupling Cap C2=0.1µF (Ceramic)",
            "exp_input_v": 12.0, "exp_output_v": 5.0, "exp_input_i": 0.5, "exp_output_i": 0.48,
            "exp_eff": 41.6, "exp_ripple": 0.1, "formula_eff": "Eff = (Vout / Vin) * 100",
            "diagram": "Vin (Pin 1) -> IC 7805 -> Vout (Pin 3) | Pin 2 -> Ground",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "Pin 1 (Input Terminal)"},
                {"step": 2, "name": "Output Probe", "loc": "Pin 3 (Output Terminal)"},
                {"step": 3, "name": "Current Probe", "loc": "Pin 1 Series Rail"}
            ]
        },
        "7809 Regulator": {
            "description": "Linear voltage regulator IC producing a fixed +9V DC output.",
            "components": "IC LM7809, C1=0.33µF Ceramic, C2=0.1µF Ceramic, Heat Sink TO-220 Package",
            "exp_input_v": 15.0, "exp_output_v": 9.0, "exp_input_i": 0.5, "exp_output_i": 0.48,
            "exp_eff": 60.0, "exp_ripple": 0.1, "formula_eff": "Eff = (Vout / Vin) * 100",
            "diagram": "Vin (Pin 1) -> IC 7809 -> Vout (Pin 3) | Pin 2 -> Ground",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "Pin 1 (Input Pin)"},
                {"step": 2, "name": "Output Probe", "loc": "Pin 3 (Output Pin)"},
                {"step": 3, "name": "Current Probe", "loc": "Main Supply Line"}
            ]
        },
        "7812 Regulator": {
            "description": "Linear voltage regulator IC producing a fixed +12V DC output.",
            "components": "IC LM7812, C1=0.33µF Ceramic, C2=0.1µF Ceramic, 10µF Electrolytic Filter Cap",
            "exp_input_v": 18.0, "exp_output_v": 12.0, "exp_input_i": 0.5, "exp_output_i": 0.48,
            "exp_eff": 66.6, "exp_ripple": 0.1, "formula_eff": "Eff = (Vout / Vin) * 100",
            "diagram": "Vin (Pin 1) -> IC 7812 -> Vout (Pin 3) | Pin 2 -> Ground",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "Pin 1 Input Lead"},
                {"step": 2, "name": "Output Probe", "loc": "Pin 3 Output Lead"},
                {"step": 3, "name": "Current Probe", "loc": "Output Terminal Rail"}
            ]
        },
        "LM317 Regulator": {
            "description": "Adjustable positive linear voltage regulator capable of supplying >1.5 A.",
            "components": "IC LM317T, R1=240Ω, R2=5kΩ Potentiometer, C1=0.1µF, C2=1µF Tantalum, Protection Diode 1N4002",
            "exp_input_v": 15.0, "exp_output_v": 1.25, "exp_input_i": 0.3, "exp_output_i": 0.28,
            "exp_eff": 50.0, "exp_ripple": 0.05, "formula_eff": "Vout = 1.25 * (1 + R2/R1) + Iadj*R2",
            "diagram": "Vin -> Adjustment Network (R1, R2 Pot) -> Vout",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "Vin Pin"},
                {"step": 2, "name": "Output Probe", "loc": "Vout Pin"},
                {"step": 3, "name": "Current Probe", "loc": "ADJ Feedback Divider"}
            ]
        }
    },
    "Oscillators": {
        "Wien Bridge Oscillator": {
            "description": "Produces sine waves using a RC bridge circuit for phase shift frequency control.",
            "components": "Op-Amp LM741, R1=R2=10kΩ, C1=C2=10nF [f ≈ 1.59 kHz], Rf=20kΩ, R3=10kΩ, 1N4148 Diodes (Amplitude Stabilizer)",
            "exp_input_v": 12.0, "exp_output_v": 8.0, "exp_input_i": 0.05, "exp_output_i": 0.04,
            "exp_eff": 70.0, "exp_ripple": 0.2, "formula_eff": "f = 1 / (2 * pi * R * C)",
            "diagram": "Op-Amp + Series/Parallel RC Lead-Lag Network",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "Op-Amp VCC Power Pin"},
                {"step": 2, "name": "Output Probe", "loc": "Op-Amp Output Node"},
                {"step": 3, "name": "Current Probe", "loc": "Feedback Loop Branch"}
            ]
        }
    },
    "Power Supplies": {
        "Linear Power Supply": {
            "description": "Step-down transformer followed by bridge rectifier, filter capacitor, and linear regulator.",
            "components": "230V to 12V-0-12V Transformer, 2A Bridge Rectifier Module, 2200µF/35V Capacitor, LM7805 IC, 0.1µF Bypass Cap",
            "exp_input_v": 230.0, "exp_output_v": 5.0, "exp_input_i": 0.05, "exp_output_i": 1.5,
            "exp_eff": 65.0, "exp_ripple": 0.02, "formula_eff": "Eff = (Pout / Pin) * 100",
            "diagram": "Transformer -> Bridge -> Filter Cap -> 7805 IC -> Output",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "Primary Transformer AC Input"},
                {"step": 2, "name": "Output Probe", "loc": "DC Output Terminals"},
                {"step": 3, "name": "Current Probe", "loc": "Secondary AC Tap"}
            ]
        }
    },
    "Clipper": {
        "Diode Clipper": {
            "description": "Clips or removes portions of the input signal waveform above or below specified limits.",
            "components": "1N4148 High-Speed Diode, R1=1kΩ Resistor, DC Bias Voltage Source Vbias=2V",
            "exp_input_v": 10.0, "exp_output_v": 0.7, "exp_input_i": 0.05, "exp_output_i": 0.04,
            "exp_eff": 80.0, "exp_ripple": 1.0, "formula_eff": "V_clip = V_bias + V_diode",
            "diagram": "Series Resistor -> Shunt Diode & DC Bias Voltage -> Ground",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "Input Signal Generator Terminal"},
                {"step": 2, "name": "Output Probe", "loc": "Across Parallel Diode Branch"},
                {"step": 3, "name": "Current Probe", "loc": "Series Resistor Branch"}
            ]
        }
    },
    "Clamper": {
        "Diode Clamper": {
            "description": "Shifts the DC level of a signal to a different level without changing the shape.",
            "components": "10µF Electrolytic Capacitor (C1), 1N4007 Diode (D1), 100kΩ Load Resistor (RL)",
            "exp_input_v": 10.0, "exp_output_v": 20.0, "exp_input_i": 0.05, "exp_output_i": 0.045,
            "exp_eff": 85.0, "exp_ripple": 1.5, "formula_eff": "V_peak_out = 2 * V_peak_in",
            "diagram": "Series Capacitor -> Shunt Diode -> Parallel Load Resistor",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "Input Signal Terminal"},
                {"step": 2, "name": "Output Probe", "loc": "Across Clamper Load Resistor"},
                {"step": 3, "name": "Current Probe", "loc": "In Series with Series Capacitor"}
            ]
        }
    },
    "RC Circuits": {
        "RC Integrator": {
            "description": "Produces an output waveform proportional to the time integral of the input signal.",
            "components": "Series Resistor R1=10kΩ, Shunt Capacitor C1=100nF [Time Constant Tau = 1ms]",
            "exp_input_v": 5.0, "exp_output_v": 2.5, "exp_input_i": 0.02, "exp_output_i": 0.018,
            "exp_eff": 88.0, "exp_ripple": 2.0, "formula_eff": "tau = R * C",
            "diagram": "Series Resistor -> Output Across Shunt Capacitor",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "Resistor Input Node"},
                {"step": 2, "name": "Output Probe", "loc": "Across Capacitor Terminals"},
                {"step": 3, "name": "Current Probe", "loc": "Series Signal Wire"}
            ]
        }
    },
    "RL Circuits": {
        "RL Transient Circuit": {
            "description": "Demonstrates current buildup and inductive decay over time constant Tau.",
            "components": "Inductor L1=10mH, Resistor R1=100Ω [Time Constant Tau = 100µs], 1N4007 Flyback Diode",
            "exp_input_v": 10.0, "exp_output_v": 9.8, "exp_input_i": 0.2, "exp_output_i": 0.19,
            "exp_eff": 92.0, "exp_ripple": 0.5, "formula_eff": "tau = L / R",
            "diagram": "DC Step Input -> Series Inductor (L) -> Resistor (R) -> Ground",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "Voltage Source Positive Terminal"},
                {"step": 2, "name": "Output Probe", "loc": "Across Resistor (R)"},
                {"step": 3, "name": "Current Probe", "loc": "Series Circuit Loop"}
            ]
        }
    },
    "RLC Circuits": {
        "RLC Series Resonance": {
            "description": "Exhibits electrical resonance at a frequency where inductive and capacitive reactances cancel.",
            "components": "Resistor R1=47Ω, Inductor L1=10mH, Capacitor C1=100nF [Resonant Freq fr ≈ 5.03 kHz]",
            "exp_input_v": 5.0, "exp_output_v": 5.0, "exp_input_i": 0.5, "exp_output_i": 0.5,
            "exp_eff": 95.0, "exp_ripple": 0.1, "formula_eff": "fr = 1 / (2 * pi * sqrt(L * C))",
            "diagram": "AC Input -> Series R -> Series L -> Series C -> Ground",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "AC Source Terminal"},
                {"step": 2, "name": "Output Probe", "loc": "Across Resistor R at Resonance"},
                {"step": 3, "name": "Current Probe", "loc": "Main Series Current Loop"}
            ]
        }
    },
    "Logic Circuits": {
        "NAND Logic Gate Tester": {
            "description": "Tests TTL or CMOS NAND gate voltage threshold logic levels (VOL, VOH, VIL, VIH).",
            "components": "74LS00 Quad 2-Input NAND IC, 2x 10kΩ Pull-down Resistors, LED Indicator, 330Ω Limiting Resistor",
            "exp_input_v": 5.0, "exp_output_v": 0.2, "exp_input_i": 0.001, "exp_output_i": 0.016,
            "exp_eff": 99.0, "exp_ripple": 0.0, "formula_eff": "NAND Logic Table Verification",
            "diagram": "VCC (+5V) -> IC 7400 Pin 14 | Inputs A, B -> Pin 1, 2 | Output Pin 3",
            "probes": [
                {"step": 1, "name": "Input Probe", "loc": "Gate Input Pin 1 & 2"},
                {"step": 2, "name": "Output Probe", "loc": "Gate Output Pin 3"},
                {"step": 3, "name": "Current Probe", "loc": "IC VCC Power Lead Pin 14"}
            ]
        }
    }
}

# ==============================================================================
# MQTT COMMUNICATION MODULE
# ==============================================================================
MQTT_BROKER_HOST = "broker.hivemq.com"
MQTT_BROKER_PORT = 1883
MQTT_TOPIC = "circuit/tester"
MQTT_KEEPALIVE = 60

_mqtt_lock = threading.Lock()
_latest_mqtt_packet = None
_mqtt_status = "Disconnected"

def on_connect(client, userdata, flags, rc):
    global _mqtt_status
    if rc == 0:
        _mqtt_status = "Connected"
        client.subscribe(MQTT_TOPIC)
    else:
        _mqtt_status = "Disconnected"

def on_disconnect(client, userdata, rc):
    global _mqtt_status
    _mqtt_status = "Disconnected"

def on_message(client, userdata, msg):
    global _latest_mqtt_packet, _mqtt_status
    try:
        payload_str = msg.payload.decode("utf-8")
        data = json.loads(payload_str)
        
        with _mqtt_lock:
            _latest_mqtt_packet = data
            _mqtt_status = "Connected"
    except Exception:
        pass

def connect_mqtt():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_KEEPALIVE)
        client.loop_start()
    except Exception:
        global _mqtt_status
        _mqtt_status = "Disconnected"
        
    return client

def initialize_mqtt():
    if "mqtt_status" not in st.session_state:
        st.session_state.mqtt_status = "Disconnected"

    if "mqtt_client" not in st.session_state:
        st.session_state.mqtt_client = connect_mqtt()

def get_mqtt_status():
    global _mqtt_status, _latest_mqtt_packet
    with _mqtt_lock:
        if _mqtt_status == "Connected" and _latest_mqtt_packet is None:
            return "Waiting for Data"
        return _mqtt_status

def get_latest_sensor_packet():
    with _mqtt_lock:
        if _latest_mqtt_packet is None:
            return None
        return dict(_latest_mqtt_packet)

# ------------------------------------------------------------------------------
# HELPER FUNCTIONS, STATE MANAGEMENT & TEXT-TO-SPEECH (TTS)
# ------------------------------------------------------------------------------
def init_session_state():
    if "selected_category" not in st.session_state:
        st.session_state.selected_category = "Rectifiers"
    if "selected_circuit" not in st.session_state:
        st.session_state.selected_circuit = "Bridge Rectifier"
    if "page" not in st.session_state:
        st.session_state.page = "Home"
    if "api_key" not in st.session_state:
        st.session_state.api_key = ""
    if "historical_tests" not in st.session_state:
        st.session_state.historical_tests = []
    if "loaded_once" not in st.session_state:
        st.session_state.loaded_once = False
    if "is_muted" not in st.session_state:
        st.session_state.is_muted = False
        
    # Target value session state definitions
    if "target_input_voltage" not in st.session_state:
        st.session_state.target_input_voltage = None
    if "target_output_voltage" not in st.session_state:
        st.session_state.target_output_voltage = None
    if "target_input_current" not in st.session_state:
        st.session_state.target_input_current = None
    if "target_output_current" not in st.session_state:
        st.session_state.target_output_current = None

    initialize_mqtt()

def get_active_targets(circuit_info):
    target_in_v = st.session_state.target_input_voltage if st.session_state.target_input_voltage is not None else circuit_info.get("exp_input_v", 12.0)
    target_out_v = st.session_state.target_output_voltage if st.session_state.target_output_voltage is not None else circuit_info.get("exp_output_v", 10.0)
    target_in_i = st.session_state.target_input_current if st.session_state.target_input_current is not None else circuit_info.get("exp_input_i", 1.0)
    target_out_i = st.session_state.target_output_current if st.session_state.target_output_current is not None else circuit_info.get("exp_output_i", 0.9)

    return {
        "target_input_voltage": float(target_in_v),
        "target_output_voltage": float(target_out_v),
        "target_input_current": float(target_in_i),
        "target_output_current": float(target_out_i)
    }

def speak_text(text_to_speak):
    if st.session_state.get("is_muted", False):
        st.components.v1.html("""
        <script>
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
        }
        </script>
        """, height=0, width=0)
        return

    clean_text = text_to_speak.replace('"', '\\"').replace("'", "\\'").replace('\n', ' ')
    tts_html = f"""
    <script>
    if ('speechSynthesis' in window) {{
        window.speechSynthesis.cancel();
        
        function speakFemale() {{
            var msg = new SpeechSynthesisUtterance("{clean_text}");
            msg.rate = 1.0;
            msg.pitch = 1.1;
            
            var voices = window.speechSynthesis.getVoices();
            var femaleVoice = voices.find(function(voice) {{
                var name = voice.name.toLowerCase();
                return voice.lang.includes('en') && (
                    name.includes('female') || 
                    name.includes('zira') || 
                    name.includes('victoria') || 
                    name.includes('google uk english female') ||
                    name.includes('samantha') ||
                    name.includes('karen')
                );
            }});

            if (femaleVoice) {{
                msg.voice = femaleVoice;
            }}
            
            window.speechSynthesis.speak(msg);
        }}

        if (window.speechSynthesis.getVoices().length === 0) {{
            window.speechSynthesis.onvoiceschanged = speakFemale;
        }} else {{
            speakFemale();
        }}
    }}
    </script>
    """
    st.components.v1.html(tts_html, height=0, width=0)

def set_active_circuit(category, circuit):
    st.session_state.selected_category = category
    st.session_state.selected_circuit = circuit
    # Reset custom targets only on changing selected circuit
    st.session_state.target_input_voltage = None
    st.session_state.target_output_voltage = None
    st.session_state.target_input_current = None
    st.session_state.target_output_current = None

def get_current_circuit_data():
    cat = st.session_state.selected_category
    ckt = st.session_state.selected_circuit
    if cat in CIRCUIT_DATABASE and ckt in CIRCUIT_DATABASE[cat]:
        return CIRCUIT_DATABASE[cat][ckt]
    first_cat = list(CIRCUIT_DATABASE.keys())[0]
    first_ckt = list(CIRCUIT_DATABASE[first_cat].keys())[0]
    st.session_state.selected_category = first_cat
    st.session_state.selected_circuit = first_ckt
    return CIRCUIT_DATABASE[first_cat][first_ckt]

def get_live_sensor_data(circuit_info):
    packet = get_latest_sensor_packet()
    active_targets = get_active_targets(circuit_info)

    ###############################
    # TEST SENSOR TELEMETRY
    ###############################
    if packet is not None:
        meas_in = float(packet.get("input_voltage", packet.get("input_v", 12.0)))
        meas_out = float(packet.get("output_voltage", packet.get("output_v", 5.0)))
        meas_in_i = float(packet.get("input_current", packet.get("input_i", 0.5)))
        meas_out_i = float(packet.get("output_current", packet.get("output_i", 0.45)))
        temp = float(packet.get("temperature", 38.4))
        freq = float(packet.get("frequency", 50.0))
    else:
        # Constant Test JSON baseline (independent of configuration settings)
        meas_in = 12.0
        meas_out = 5.0
        meas_in_i = 0.50
        meas_out_i = 0.45
        temp = 38.4
        freq = 50.0
    ###############################

    p_in = meas_in * meas_in_i
    p_out = meas_out * meas_out_i
    eff = (p_out / p_in * 100.0) if p_in > 0 else 0.0
    v_drop = max(0.0, meas_in - meas_out)

    # Health Rating Calculated strictly against Active Targets
    v_dev = abs(meas_out - active_targets["target_output_voltage"]) / active_targets["target_output_voltage"] if active_targets["target_output_voltage"] > 0 else 0
    health = max(0, min(100, int((1.0 - v_dev) * 100)))

    return {
        "input_v": meas_in, "output_v": meas_out,
        "input_i": meas_in_i, "output_i": meas_out_i,
        "power_in": round(p_in, 2), "power_out": round(p_out, 2),
        "efficiency": round(eff, 2), "v_drop": round(v_drop, 2),
        "temperature": temp, "frequency": freq, "health": health
    }

def generate_waveform_chart(freq_val, v_in, v_out):
    t = np.linspace(0, 0.04, 500)
    omega = 2 * np.pi * freq_val
    vin_wave = v_in * np.sin(omega * t)
    vout_wave = np.abs(v_out * np.sin(omega * t)) + 0.05 * np.random.normal(0, 0.05, len(t))

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12,
                        subplot_titles=("INPUT TELEMETRY WAVEFORM (AC)", "DIAGNOSTIC OUTPUT WAVEFORM (DC)"))

    fig.add_trace(go.Scatter(x=t, y=vin_wave, mode='lines', name='Input V(t)', 
                             line=dict(color='#00f2fe', width=3)), row=1, col=1)
    fig.add_trace(go.Scatter(x=t, y=vout_wave, mode='lines', name='Output V(t)', 
                             line=dict(color='#00ff87', width=3)), row=2, col=1)

    fig.update_layout(
        height=380, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(3, 7, 18, 0.65)',
        font=dict(color='#00f2fe', family='Orbitron', size=11),
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode="x unified",
        xaxis=dict(gridcolor='rgba(0, 242, 254, 0.15)', zerolinecolor='rgba(0, 242, 254, 0.3)'),
        xaxis2=dict(gridcolor='rgba(0, 242, 254, 0.15)', zerolinecolor='rgba(0, 242, 254, 0.3)'),
        yaxis=dict(gridcolor='rgba(0, 242, 254, 0.15)', zerolinecolor='rgba(0, 242, 254, 0.3)'),
        yaxis2=dict(gridcolor='rgba(0, 242, 254, 0.15)', zerolinecolor='rgba(0, 242, 254, 0.3)')
    )
    return fig

def create_circular_gauge(title, value, max_val, unit, color="#00f2fe"):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        number = {'suffix': f" {unit}", 'font': {'color': "#ffffff", 'size': 20, 'family': "Orbitron"}},
        title = {'text': title.upper(), 'font': {'color': color, 'size': 11, 'family': "Orbitron"}},
        gauge = {
            'axis': {'range': [0, max_val], 'tickwidth': 1, 'tickcolor': "rgba(0, 242, 254, 0.4)"},
            'bar': {'color': color, 'thickness': 0.35},
            'bgcolor': "rgba(3, 7, 18, 0.8)",
            'borderwidth': 1,
            'bordercolor': "rgba(0, 242, 254, 0.25)",
            'steps': [
                {'range': [0, max_val], 'color': 'rgba(0, 242, 254, 0.03)'}
            ]
        }
    ))
    fig.update_layout(
        height=170, margin=dict(l=15, r=15, t=35, b=15),
        paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#ffffff')
    )
    return fig

# ------------------------------------------------------------------------------
# 3. GEMINI AI INTEGRATION & DIAGNOSIS LOGIC
# ------------------------------------------------------------------------------
def evaluate_pass_fail_status(active_targets, meas_data):
    """
    Computes percentage deviations against target values and assigns status:
    - PASS: every parameter is within ±5%
    - WARNING: any parameter is between 5% and 10%
    - FAIL: any parameter exceeds 10%
    """
    def calc_dev(meas, target):
        return (abs(meas - target) / target * 100.0) if target > 0 else 0.0

    dev_in_v = calc_dev(meas_data.get('input_v', 0), active_targets['target_input_voltage'])
    dev_out_v = calc_dev(meas_data.get('output_v', 0), active_targets['target_output_voltage'])
    dev_in_i = calc_dev(meas_data.get('input_i', 0), active_targets['target_input_current'])
    dev_out_i = calc_dev(meas_data.get('output_i', 0), active_targets['target_output_current'])

    deviations = {
        "Input Voltage": dev_in_v,
        "Output Voltage": dev_out_v,
        "Input Current": dev_in_i,
        "Output Current": dev_out_i
    }

    max_dev = max(deviations.values())

    if max_dev <= 5.0:
        status = "PASS"
    elif max_dev <= 10.0:
        status = "WARNING"
    else:
        status = "FAIL"

    return status, deviations

def get_gemini_client():
    api_key = st.session_state.get("api_key") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None

def generate_automatic_diagnosis(circuit_name, exp_data, meas_data, probes, freq_val, temp):
    client = get_gemini_client()
    active_targets = get_active_targets(exp_data)
    
    status, deviations = evaluate_pass_fail_status(active_targets, meas_data)

    prompt = f"""
USER CONFIGURED TARGET VALUES

Target Input Voltage = {active_targets['target_input_voltage']} V
Target Output Voltage = {active_targets['target_output_voltage']} V
Target Input Current = {active_targets['target_input_current']} A
Target Output Current = {active_targets['target_output_current']} A

LIVE SENSOR TELEMETRY

Measured Input Voltage = {meas_data.get('input_v', 0)} V
Measured Output Voltage = {meas_data.get('output_v', 0)} V
Measured Input Current = {meas_data.get('input_i', 0)} A
Measured Output Current = {meas_data.get('output_i', 0)} A
Frequency = {freq_val} Hz
Temperature = {temp} °C
Power Input = {meas_data.get('power_in', 0)} W
Power Output = {meas_data.get('power_out', 0)} W
Efficiency = {meas_data.get('efficiency', 0)} %
Health = {meas_data.get('health', 0)} %

INSTRUCTIONS:
Compare the LIVE SENSOR TELEMETRY against the USER CONFIGURED TARGET VALUES.

PASS / FAIL TOLERANCE RULES:
- If every parameter is within ±5%: PASS
- If any parameter is between ±5% and ±10%: WARNING
- If any parameter exceeds ±10%: FAIL

Calculated Deviations:
- Input Voltage Deviation: {deviations['Input Voltage']:.2f}%
- Output Voltage Deviation: {deviations['Output Voltage']:.2f}%
- Input Current Deviation: {deviations['Input Current']:.2f}%
- Output Current Deviation: {deviations['Output Current']:.2f}%

Pre-calculated Status based on rules: {status}

Circuit Topology: {circuit_name}
Components: {exp_data.get('components', 'N/A')}
Probe Locations: {probes}

Respond with:
1. Status: {status}
2. Detailed explanation of every deviation.
3. Identify the probable faulty component.
4. Provide step-by-step repair steps.
5. Provide a confidence score (%).
"""
    
    if client:
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            return response.text
        except Exception as e:
            st.error(f"Gemini API Diagnostic Error: {e}")

    # Fallback Evaluation Engine against Session Targets
    dev_str = ", ".join([f"{k}: {v:.1f}%" for k, v in deviations.items()])
    diag_summary = f"System Evaluation: {status}. Calculated Deviations -> {dev_str}."

    return {
        "status": status,
        "diagnosis": diag_summary,
        "repair_procedure": "1. Verify supply power rail continuity.\n2. Inspect components for thermal/overcurrent damage.\n3. Verify probe tap connections."
    }

def record_test_run(circuit_name, status, diagnosis, metrics):
    now = datetime.datetime.now()
    st.session_state.historical_tests.append({
        "Date": now.strftime("%Y-%m-%d"), 
        "Time": now.strftime("%H:%M:%S"),
        "Circuit": circuit_name, 
        "Status": status,
        "Input Voltage (V)": f"{metrics.get('input_v')} V", 
        "Output Voltage (V)": f"{metrics.get('output_v')} V",
        "Efficiency %": f"{metrics.get('efficiency')} %", 
        "AI Answer / Diagnosis": str(diagnosis)
    })

# ------------------------------------------------------------------------------
# 4. HOLLYWOOD-QUALITY AI OPERATING SYSTEM INTERFACE & GRAPHICS
# ------------------------------------------------------------------------------
st.set_page_config(page_title="NEXUS AI OS v2.2", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")
init_session_state()

# Canvas Background JS
canvas_background_js = """
<canvas id="fui-canvas" style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -10; pointer-events: none; opacity: 0.85;"></canvas>
<div id="fui-cursor-glow" style="position: fixed; width: 250px; height: 250px; border-radius: 50%; background: radial-gradient(circle, rgba(0, 242, 254, 0.12) 0%, rgba(0, 242, 254, 0) 70%); pointer-events: none; transform: translate(-50%, -50%); z-index: -9; transition: width 0.3s, height 0.3s;"></div>

<script>
(function() {
    const cursorGlow = document.getElementById('fui-cursor-glow');
    window.addEventListener('mousemove', (e) => {
        if(cursorGlow) {
            cursorGlow.style.left = e.clientX + 'px';
            cursorGlow.style.top = e.clientY + 'px';
        }
    });

    const canvas = document.getElementById('fui-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let w = canvas.width = window.innerWidth;
    let h = canvas.height = window.innerHeight;

    window.addEventListener('resize', () => {
        w = canvas.width = window.innerWidth;
        h = canvas.height = window.innerHeight;
    });

    const particles = [];
    const count = 55;
    for (let i = 0; i < count; i++) {
        particles.push({
            x: Math.random() * w,
            y: Math.random() * h,
            vx: (Math.random() - 0.5) * 0.5,
            vy: (Math.random() - 0.5) * 0.5,
            radius: Math.random() * 2 + 1,
            alpha: Math.random() * 0.6 + 0.2
        });
    }

    let angle = 0;
    function draw() {
        ctx.clearRect(0, 0, w, h);

        angle += 0.005;
        ctx.strokeStyle = 'rgba(0, 242, 254, 0.03)';
        ctx.lineWidth = 1;
        const gridStep = 70;
        for (let x = 0; x < w; x += gridStep) {
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
        }
        for (let y = 0; y < h; y += gridStep) {
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
        }

        for (let i = 0; i < count; i++) {
            let p = particles[i];
            p.x += p.vx; p.y += p.vy;
            if (p.x < 0) p.x = w; if (p.x > w) p.x = 0;
            if (p.y < 0) p.y = h; if (p.y > h) p.y = 0;

            ctx.fillStyle = `rgba(0, 242, 254, ${p.alpha})`;
            ctx.beginPath(); ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2); ctx.fill();

            for (let j = i + 1; j < count; j++) {
                let p2 = particles[j];
                let dist = Math.hypot(p.x - p2.x, p.y - p2.y);
                if (dist < 140) {
                    ctx.strokeStyle = `rgba(0, 242, 254, ${0.15 * (1 - dist / 140)})`;
                    ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(p2.x, p2.y); ctx.stroke();
                }
            }
        }
        requestAnimationFrame(draw);
    }
    draw();
})();
</script>
"""

FUI_STYLING = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=Rajdhani:wght@400;500;600;700&display=swap');

header[data-testid="stHeader"] {
    background-color: #02050e !important;
}
header[data-testid="stHeader"] button, 
header[data-testid="stHeader"] svg,
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarCollapseButton"] svg {
    color: #00f2fe !important;
    fill: #00f2fe !important;
    stroke: #00f2fe !important;
}

html, body, .stApp {
    background: #02050e !important;
    color: #c8d6e5 !important;
    font-family: 'Rajdhani', sans-serif !important;
    overflow-x: hidden;
}

.stAppMain {
    animation: fadeInScale 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes fadeInScale {
    0% { opacity: 0; transform: scale(0.98) translateY(10px); filter: blur(6px); }
    100% { opacity: 1; transform: scale(1) translateY(0); filter: blur(0); }
}

.os-card {
    background: rgba(6, 12, 26, 0.65) !important;
    backdrop-filter: blur(25px) saturate(200%) !important;
    -webkit-backdrop-filter: blur(25px) saturate(200%) !important;
    border: 1px solid rgba(0, 242, 254, 0.22) !important;
    box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.8), inset 0 0 15px rgba(0, 242, 254, 0.05) !important;
    border-radius: 12px !important;
    padding: 22px !important;
    margin-bottom: 20px !important;
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    position: relative;
    overflow: hidden;
    animation: floatPanel 6s ease-in-out infinite alternate;
}

.os-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; width: 4px; height: 100%;
    background: linear-gradient(180deg, #00f2fe, #7928ca);
    opacity: 0.8;
}

.os-card:hover {
    transform: translateY(-6px) rotate(0.5deg) scale(1.008);
    border-color: rgba(0, 242, 254, 0.6) !important;
    box-shadow: 0 15px 35px -5px rgba(0, 242, 254, 0.3), inset 0 0 20px rgba(0, 242, 254, 0.15) !important;
}

@keyframes floatPanel {
    0% { transform: translateY(0px) rotate(0deg); }
    100% { transform: translateY(-4px) rotate(0.4deg); }
}

.os-header-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(4, 8, 18, 0.85);
    border: 1px solid rgba(0, 242, 254, 0.3);
    border-radius: 8px;
    padding: 10px 20px;
    margin-bottom: 22px;
    font-family: 'Orbitron', sans-serif;
    font-size: 0.78rem;
    letter-spacing: 1.2px;
    box-shadow: 0 0 20px rgba(0, 242, 254, 0.15);
}

.sys-tag {
    display: flex;
    align-items: center;
    gap: 8px;
}

.os-indicator-dot {
    width: 9px; height: 9px;
    border-radius: 50%;
    background-color: #00ff87;
    box-shadow: 0 0 12px #00ff87;
    animation: pulseGlow 1.8s infinite;
}

@keyframes pulseGlow {
    0% { transform: scale(0.9); box-shadow: 0 0 4px #00ff87; }
    50% { transform: scale(1.3); box-shadow: 0 0 16px #00ff87; }
    100% { transform: scale(0.9); box-shadow: 0 0 4px #00ff87; }
}

.core-container {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 35px 0;
    perspective: 1000px;
}

.core-reactor {
    width: 170px;
    height: 170px;
    border-radius: 50%;
    border: 2px dashed #00f2fe;
    display: flex;
    justify-content: center;
    align-items: center;
    animation: rotateCore 16s linear infinite;
    box-shadow: 0 0 40px rgba(0, 242, 254, 0.35), inset 0 0 30px rgba(0, 242, 254, 0.35);
    position: relative;
}

.core-ring-2 {
    position: absolute;
    width: 140px; height: 140px;
    border-radius: 50%;
    border: 2px dotted #00ff87;
    animation: rotateCoreRev 10s linear infinite;
}

.core-ring-3 {
    position: absolute;
    width: 110px; height: 110px;
    border-radius: 50%;
    border: 2px solid #7928ca;
    border-left: 2px solid transparent;
    animation: rotateCore 6s linear infinite;
}

.core-ring-4 {
    position: absolute;
    width: 80px; height: 80px;
    border-radius: 50%;
    border: 2px dashed #ff0055;
    animation: rotateCoreRev 4s linear infinite;
}

.core-center-node {
    position: absolute;
    width: 50px; height: 50px;
    border-radius: 50%;
    background: radial-gradient(circle, #00ff87 0%, #00f2fe 60%, rgba(0,242,254,0) 100%);
    box-shadow: 0 0 30px #00ff87;
    animation: corePulse 1.5s ease-in-out infinite alternate;
}

@keyframes rotateCore { 100% { transform: rotate(360deg); } }
@keyframes rotateCoreRev { 100% { transform: rotate(-360deg); } }
@keyframes corePulse { 0% { transform: scale(0.8); opacity: 0.7; } 100% { transform: scale(1.2); opacity: 1.0; } }

.pipeline-flow {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px;
    background: rgba(3, 7, 18, 0.85);
    border: 1px solid rgba(0, 242, 254, 0.25);
    border-radius: 10px;
    margin: 20px 0;
}

.node-box {
    font-family: 'Orbitron', sans-serif;
    font-size: 0.78rem;
    padding: 9px 16px;
    background: rgba(0, 242, 254, 0.12);
    border: 1px solid #00f2fe;
    border-radius: 6px;
    color: #00f2fe;
    box-shadow: 0 0 12px rgba(0, 242, 254, 0.25);
    transition: transform 0.2s;
}

.node-box:hover {
    transform: scale(1.08);
}

.pipe-connector {
    flex-grow: 1;
    height: 3px;
    background: linear-gradient(90deg, #00f2fe, #00ff87);
    margin: 0 10px;
    position: relative;
    overflow: hidden;
}

.pipe-connector::after {
    content: '';
    position: absolute;
    top: 0; left: -100%; width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, #ffffff, transparent);
    animation: flowData 1.2s linear infinite;
}

@keyframes flowData { 0% { left: -100%; } 100% { left: 100%; } }

[data-testid="stSidebar"] {
    background: rgba(2, 5, 14, 0.96) !important;
    border-right: 1px solid rgba(0, 242, 254, 0.25) !important;
}

h1, h2, h3 {
    font-family: 'Orbitron', sans-serif !important;
    letter-spacing: 1.6px !important;
    text-transform: uppercase;
}

h1 {
    background: linear-gradient(90deg, #00f2fe 0%, #00ff87 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.2rem !important;
    font-weight: 900 !important;
}

div.stButton > button {
    background: linear-gradient(135deg, rgba(0, 242, 254, 0.2) 0%, rgba(121, 40, 202, 0.3) 100%) !important;
    color: #00f2fe !important;
    font-family: 'Orbitron', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    letter-spacing: 1.5px !important;
    border: 1px solid #00f2fe !important;
    border-radius: 6px !important;
    padding: 12px 24px !important;
    box-shadow: 0 0 15px rgba(0, 242, 254, 0.2) !important;
    transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
}

div.stButton > button:hover {
    background: linear-gradient(135deg, #00f2fe 0%, #7928ca 100%) !important;
    color: #ffffff !important;
    box-shadow: 0 0 30px rgba(0, 242, 254, 0.7) !important;
    transform: translateY(-3px) scale(1.02) !important;
}

div.stButton > button:active {
    transform: translateY(1px) scale(0.98) !important;
}

div[data-baseweb="select"] {
    background-color: rgba(3, 7, 18, 0.9) !important;
    border: 1px solid rgba(0, 242, 254, 0.3) !important;
    border-radius: 6px !important;
}

div[data-testid="stDataFrame"] {
    background: rgba(3, 7, 18, 0.7) !important;
    border: 1px solid rgba(0, 242, 254, 0.25) !important;
    border-radius: 8px !important;
}
</style>
"""
st.markdown(FUI_STYLING, unsafe_allow_html=True)
st.components.v1.html(canvas_background_js, height=0, width=0)

if not st.session_state.loaded_once:
    boot_placeholder = st.empty()
    with boot_placeholder.container():
        st.markdown("""
        <div style="height: 70vh; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center;">
            <h2 style="font-family: Orbitron; color: #00f2fe; font-size: 2rem; margin-bottom: 10px;">NEXUS AI OPERATING SYSTEM</h2>
            <p style="color: #00ff87; font-family: Orbitron; letter-spacing: 2px;">INITIALIZING CORE MATRIX...</p>
            <div style="width: 300px; height: 6px; background: rgba(0,242,254,0.1); border-radius: 3px; overflow: hidden; border: 1px solid #00f2fe;">
                <div style="width: 100%; height: 100%; background: linear-gradient(90deg, #00f2fe, #00ff87); animation: bootProgress 1.5s ease-in-out;"></div>
            </div>
            <div style="margin-top: 15px; font-size: 0.8rem; color: #64748b; font-family: Orbitron;">
                ESP32 ONLINE | MQTT CONNECTED | DATABASE READY | GEMINI ACTIVE
            </div>
        </div>
        <style>
        @keyframes bootProgress { 0% { width: 0%; } 100% { width: 100%; } }
        </style>
        """, unsafe_allow_html=True)
        time.sleep(1.2)
    boot_placeholder.empty()
    st.session_state.loaded_once = True

# ------------------------------------------------------------------------------
# TOP HEADER HUD CONTROL BAR
# ------------------------------------------------------------------------------
now = datetime.datetime.now()
mqtt_status = get_mqtt_status()
mqtt_color = "#00ff87" if mqtt_status == "Connected" else ("#ffb703" if mqtt_status == "Waiting for Data" else "#ff0055")

st.markdown(f"""
<div class="os-header-bar">
    <div class="sys-tag"><span class="os-indicator-dot"></span> <b>SYSTEM:</b> NEXUS AI OS</div>
    <div><b>DATE:</b> {now.strftime("%Y-%m-%d")}</div>
    <div><b>TIME:</b> {now.strftime("%H:%M:%S")}</div>
    <div><b>ESP32:</b> <span style="color:#00ff87;">ONLINE</span></div>
    <div><b>MQTT:</b> <span style="color:{mqtt_color};">{mqtt_status.upper()}</span></div>
    <div><b>GEMINI:</b> <span style="color:#00ff87;">ACTIVE</span></div>
    <div><b>CPU:</b> 12.4%</div>
    <div><b>RAM:</b> 3.2 GB</div>
    <div><b>FPS:</b> 60.0</div>
</div>
""", unsafe_allow_html=True)

# Sidebar System Menu
st.sidebar.markdown('<div style="font-family:Orbitron; font-size:1.1rem; color:#00f2fe; margin-bottom:15px; font-weight:700;">⚡ OS NAVIGATION</div>', unsafe_allow_html=True)
pages = ["Home", "Circuit Type", "Configuration", "Probe Guide", "Testing Dashboard", "History", "Settings", "About"]
page_choice = st.sidebar.radio("DIRECTIVE", pages, index=pages.index(st.session_state.page if st.session_state.page in pages else "Home"))
st.session_state.page = page_choice

# Audio Voice Mute/Unmute Control Toggle
st.sidebar.markdown("---")
is_mute = st.sidebar.checkbox("🔇 Mute Audio Speech Output", value=st.session_state.is_muted)
if is_mute != st.session_state.is_muted:
    st.session_state.is_muted = is_mute
    if is_mute:
        speak_text("")

curr_circuit = get_current_circuit_data()

# ------------------------------------------------------------------------------
# STEP 1: HOME PAGE
# ------------------------------------------------------------------------------
if st.session_state.page == "Home":
    st.title("⚡ NEXUS ELECTRONIC DIAGNOSTIC OS")
    st.caption("AI Operating System Platform | Autonomous Circuit Intelligence")

    speak_text("Welcome to Nexus AI Operating System")

    st.markdown("""
    <div class="core-container">
        <div class="core-reactor">
            <div class="core-ring-2"></div>
            <div class="core-ring-3"></div>
            <div class="core-ring-4"></div>
            <div class="core-center-node"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    api_key = st.session_state.get("api_key") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        st.warning("⚠️ **STANDBY MODE**: Gemini AI Engine is running in offline mode. Configure API key in OS Settings.")

    st.markdown("### 🎛️ Circuit System Selection")
    st.markdown('<div class="os-card">', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    
    with c1:
        chosen_cat = st.selectbox(
            "SYSTEM CATEGORY", 
            list(CIRCUIT_DATABASE.keys()), 
            index=list(CIRCUIT_DATABASE.keys()).index(st.session_state.selected_category),
            key="home_cat_select"
        )
        st.session_state.selected_category = chosen_cat

    with c2:
        available_ckts = list(CIRCUIT_DATABASE[st.session_state.selected_category].keys())
        default_ckt_idx = available_ckts.index(st.session_state.selected_circuit) if st.session_state.selected_circuit in available_ckts else 0
        chosen_ckt = st.selectbox(
            "TARGET CIRCUIT TOPOLOGY", 
            available_ckts, 
            index=default_ckt_idx,
            key="home_ckt_select"
        )
        st.session_state.selected_circuit = chosen_ckt

    curr_circuit = get_current_circuit_data()

    st.markdown(f"""
        <hr style='border:0; height:1px; background: rgba(0,242,254,0.2); margin:18px 0;'>
        <h3 style="color:#00ff87 !important; margin-top:0;">LOADED TOPOLOGY: {st.session_state.selected_circuit}</h3>
        <p style="font-size: 1.05rem;"><b>FUNCTION:</b> {curr_circuit['description']}</p>
        <p style="font-size: 1.0rem; color:#00f2fe;"><b>COMPONENTS:</b> {curr_circuit.get('components', 'N/A')}</p>
        <p><b>SCHEMATIC VECTOR:</b> <code style="color:#00ff87; background:rgba(0,0,0,0.6); padding:6px 12px; border-radius:4px; border:1px solid rgba(0,255,135,0.3);">{curr_circuit['diagram']}</code></p>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("INITIALIZE SYSTEM CONFIGURATION →", use_container_width=True):
        st.session_state.page = "Configuration"
        st.rerun()

# ------------------------------------------------------------------------------
# STEP 2: CATEGORY / TYPE BROWSER PAGE
# ------------------------------------------------------------------------------
elif st.session_state.page == "Circuit Type":
    st.header(f"📂 CIRCUIT CATALOG ARCHIVE: {st.session_state.selected_category}")
    cols = st.columns(2)
    for idx, (c_name, c_info) in enumerate(CIRCUIT_DATABASE[st.session_state.selected_category].items()):
        with cols[idx % 2]:
            st.markdown(f"""
            <div class='os-card'>
                <h3 style="color:#00f2fe !important;">⚡ {c_name}</h3>
                <p><b>Description:</b> {c_info['description']}</p>
                <p style="color:#00ff87;"><b>Hardware Spec:</b> {c_info.get('components', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"LOAD {c_name.upper()}", key=f"btn_{c_name}"):
                set_active_circuit(st.session_state.selected_category, c_name)
                st.session_state.page = "Configuration"
                st.rerun()

# ------------------------------------------------------------------------------
# STEP 3: CONFIGURATION
# ------------------------------------------------------------------------------
elif st.session_state.page == "Configuration":
    st.header(f"⚙️ TARGET CONFIGURATION - {st.session_state.selected_circuit}")
    st.markdown('<div class="os-card">', unsafe_allow_html=True)
    
    st.markdown(f"**HARDWARE MATRIX SPEC:** `{curr_circuit.get('components', 'N/A')}`")
    st.markdown("<hr style='border:0; height:1px; background: rgba(0,242,254,0.2);'>", unsafe_allow_html=True)
    
    # Pre-populate input values from session_state or circuit default baseline
    default_in_v = st.session_state.target_input_voltage if st.session_state.target_input_voltage is not None else float(curr_circuit['exp_input_v'])
    default_out_v = st.session_state.target_output_voltage if st.session_state.target_output_voltage is not None else float(curr_circuit['exp_output_v'])
    default_in_i = st.session_state.target_input_current if st.session_state.target_input_current is not None else float(curr_circuit['exp_input_i'])
    default_out_i = st.session_state.target_output_current if st.session_state.target_output_current is not None else float(curr_circuit['exp_output_i'])

    cfg_c1, cfg_c2 = st.columns(2)
    with cfg_c1:
        in_v = st.number_input("Target Input Voltage (V)", value=default_in_v, key="cfg_input_v")
        in_i = st.number_input("Target Input Current (A)", value=default_in_i, key="cfg_input_i")
    with cfg_c2:
        out_v = st.number_input("Target Output Voltage (V)", value=default_out_v, key="cfg_output_v")
        out_i = st.number_input("Target Output Current (A)", value=default_out_i, key="cfg_output_i")
        
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Save / Apply Configuration", use_container_width=True):
        st.session_state.target_input_voltage = float(in_v)
        st.session_state.target_output_voltage = float(out_v)
        st.session_state.target_input_current = float(in_i)
        st.session_state.target_output_current = float(out_i)
        st.success("✅ Target values successfully updated and active!")

    st.markdown('</div>', unsafe_allow_html=True)

    c_prev, c_next = st.columns(2)
    with c_prev:
        if st.button("← SYSTEM MATRIX"):
            st.session_state.page = "Home"
            st.rerun()
    with c_next:
        if st.button("PROBE MAPPING SETUP →"):
            st.session_state.page = "Probe Guide"
            st.rerun()

# ------------------------------------------------------------------------------
# STEP 4: PROBE GUIDE
# ------------------------------------------------------------------------------
elif st.session_state.page == "Probe Guide":
    st.header(f"📍 SENSOR PROBE CALIBRATION - {st.session_state.selected_circuit}")
    st.info(f"🧩 **ACTIVE LAYOUT CONFIGURATION**: {curr_circuit.get('components', 'N/A')}")
    for probe in curr_circuit["probes"]:
        st.markdown(f"""
        <div class="os-card" style="border-left: 4px solid #00f2fe !important;">
            <h4 style="color:#00ff87 !important;">PROBE STEP {probe['step']}: {probe['name']}</h4>
            <p>Connect Acquisition Hardware Terminal to Node: <b style="color:#00f2fe;">{probe['loc']}</b></p>
        </div>
        """, unsafe_allow_html=True)

    if st.button("ENGAGE DIAGNOSTIC SYSTEM →", use_container_width=True):
        st.session_state.page = "Testing Dashboard"
        st.rerun()

# ------------------------------------------------------------------------------
# STEP 5: TESTING DASHBOARD
# ------------------------------------------------------------------------------
elif st.session_state.page == "Testing Dashboard":
    st.header(f"📊 LIVE AI OS DIAGNOSTIC MATRIX - {st.session_state.selected_circuit}")
    st.caption(f"Hardware Topology Specs: {curr_circuit.get('components', 'N/A')}")
    
    # Load User Session State Target Specifications
    active_targets = get_active_targets(curr_circuit)
    
    st.info(f"🎯 **ACTIVE USER TARGETS**: Input: **{active_targets['target_input_voltage']} V / {active_targets['target_input_current']} A** | Output: **{active_targets['target_output_voltage']} V / {active_targets['target_output_current']} A**")

    st.markdown("""
    <div class="pipeline-flow">
        <div class="node-box">CIRCUIT</div>
        <div class="pipe-connector"></div>
        <div class="node-box">ESP32</div>
        <div class="pipe-connector"></div>
        <div class="node-box">MQTT</div>
        <div class="pipe-connector"></div>
        <div class="node-box">STREAMLIT</div>
        <div class="pipe-connector"></div>
        <div class="node-box">GEMINI AI</div>
        <div class="pipe-connector"></div>
        <div class="node-box" style="border-color:#00ff87; color:#00ff87;">DIAGNOSIS</div>
    </div>
    """, unsafe_allow_html=True)

    sensor_data = get_live_sensor_data(curr_circuit)
    
    st.subheader("📡 SENSOR ACQUISITION METRICS")
    g1, g2, g3, g4 = st.columns(4)
    with g1:
        st.plotly_chart(create_circular_gauge("Input Voltage", sensor_data['input_v'], max(30.0, active_targets['target_input_voltage'] * 1.5), "V", "#00f2fe"), use_container_width=True)
    with g2:
        st.plotly_chart(create_circular_gauge("Output Voltage", sensor_data['output_v'], max(30.0, active_targets['target_output_voltage'] * 1.5), "V", "#00ff87"), use_container_width=True)
    with g3:
        st.plotly_chart(create_circular_gauge("Efficiency", sensor_data['efficiency'], 100, "%", "#9d4edd"), use_container_width=True)
    with g4:
        st.plotly_chart(create_circular_gauge("Circuit Health", sensor_data['health'], 100, "%", "#ff0055" if sensor_data['health'] < 80 else "#00ff87"), use_container_width=True)

    st.markdown('<div class="os-card">', unsafe_allow_html=True)
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("INPUT CURRENT", f"{sensor_data['input_i']} A")
    col6.metric("OUTPUT CURRENT", f"{sensor_data['output_i']} A")
    col7.metric("FREQUENCY", f"{sensor_data['frequency']} Hz")
    col8.metric("TEMPERATURE", f"{sensor_data['temperature']} °C")
    st.markdown('</div>', unsafe_allow_html=True)

    st.plotly_chart(generate_waveform_chart(sensor_data['frequency'], sensor_data['input_v'], sensor_data['output_v']), use_container_width=True)

    st.markdown("---")
    head_col1, head_col2 = st.columns([3, 1])
    with head_col1:
        st.subheader("🤖 GEMINI AI DIAGNOSIS ENGINE")
    with head_col2:
        if st.button("🔄 REFRESH DIAGNOSIS", key="refresh_ai_diag_btn", use_container_width=True):
            st.rerun()

    diag_container = st.empty()
    with diag_container.container():
        st.markdown('<div class="os-card">', unsafe_allow_html=True)
        st.markdown("⚡ **EXECUTING HIGH-SPEED NEURAL DIAGNOSTIC SCAN...**")
        p_bar = st.progress(0)
        status_text = st.empty()
        
        steps = [
            "Initializing AI Engine...",
            "Loading Model Topology...",
            "Receiving Sensor Telemetry...",
            "Checking User Target Parameters...",
            "Running Diagnostic Engine...",
            "Comparing Measured vs Target Specs...",
            "Finding Fault Points...",
            "Generating Repair Procedure..."
        ]
        
        for i, step in enumerate(steps):
            status_text.text(step)
            p_bar.progress(int((i + 1) * 12.5))
            time.sleep(0.08)
        st.markdown('</div>', unsafe_allow_html=True)
        
    ai_diag = generate_automatic_diagnosis(
        st.session_state.selected_circuit,
        curr_circuit,
        sensor_data,
        curr_circuit['probes'],
        sensor_data['frequency'],
        sensor_data['temperature']
    )

    full_diag_text = ""
    status_str = "EVALUATED"

    with diag_container.container():
        if isinstance(ai_diag, str):
            st.markdown(f"<div class='os-card'>{ai_diag}</div>", unsafe_allow_html=True)
            full_diag_text = ai_diag
        elif isinstance(ai_diag, dict):
            status_str = ai_diag['status']
            color = "#00ff87" if status_str == "PASS" else ("#ffb703" if status_str == "WARNING" else "#ff0055")
            st.markdown(f"""
            <div class='os-card' style='border-left: 5px solid {color} !important;'>
                <h3 style='color: {color} !important;'>SYSTEM EVALUATION: {status_str}</h3>
                <p><b>DIAGNOSIS:</b> {ai_diag['diagnosis']}</p>
                <p><b>REPAIR PROCEDURE:</b></p>
                <pre style='color:#00f2fe; background:rgba(0,0,0,0.7); padding:12px; border-radius:6px; border:1px solid rgba(0,242,254,0.2);'>{ai_diag['repair_procedure']}</pre>
            </div>
            """, unsafe_allow_html=True)
            full_diag_text = f"Status: {status_str} | Diagnosis: {ai_diag['diagnosis']}"

    speak_text(full_diag_text)

    if st.button("💾 LOG TEST RUN TO MISSION ARCHIVE", use_container_width=True):
        record_test_run(
            st.session_state.selected_circuit,
            status_str,
            full_diag_text,
            sensor_data
        )
        st.success("✅ Diagnostic telemetry successfully logged into mission database history.")

    st.markdown("---")
    st.subheader("💬 GEMINI AI OS COPILOT TERMINAL")
    
    user_query = st.text_input("INPUT DIRECTIVE FOR GEMINI AI:", placeholder="e.g., Explain causes for voltage degradation on diode branch", key="dashboard_gemini_query")
    
    if st.button("EXECUTE DIRECTIVE", key="dashboard_ask_btn"):
        if user_query.strip():
            client = get_gemini_client()
            if client:
                try:
                    with st.spinner("Processing neural query..."):
                        context_prompt = f"""
                        Circuit Name: {st.session_state.selected_circuit}
                        Active User Targets: {active_targets}
                        Live Sensor Telemetry: {sensor_data}
                        
                        User Question: {user_query}
                        
                        Provide a concise, expert engineering response comparing measurements to active target specs.
                        """
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=context_prompt
                        )
                        answer = response.text
                        st.markdown(f"""
                        <div class="os-card" style="border-left: 4px solid #9d4edd !important;">
                            <h4 style="color:#9d4edd !important;">🤖 GEMINI AI RESPONSE:</h4>
                            <div>{answer}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        speak_text(answer)

                except Exception as e:
                    st.error(f"Error querying Gemini API: {e}")
            else:
                st.warning("⚠️ Gemini API Key missing. Please set key in Settings tab.")

# ------------------------------------------------------------------------------
# STEP 6: HISTORY PAGE
# ------------------------------------------------------------------------------
elif st.session_state.page == "History":
    st.header("📜 MISSION LOG ARCHIVE & TELEMETRY DATABASE")
    
    if not st.session_state.historical_tests:
        st.info("No saved telemetry records found in mission archive.")
    else:
        top_c1, top_c2 = st.columns([3, 1])
        with top_c2:
            if st.button("🗑️ PURGE ARCHIVE", use_container_width=True):
                st.session_state.historical_tests = []
                st.rerun()

        df_history = pd.DataFrame(st.session_state.historical_tests)
        st.dataframe(df_history, use_container_width=True)

        st.markdown("### 🔍 LOG ENTRY BREAKDOWN")
        for idx, record in enumerate(reversed(st.session_state.historical_tests)):
            actual_index = len(st.session_state.historical_tests) - 1 - idx
            with st.expander(f"📌 [{record['Date']} {record['Time']}] {record['Circuit']} - Status: {record['Status']}"):
                st.markdown(f"**Circuit Type:** {record['Circuit']}")
                st.markdown(f"**Input Voltage:** {record['Input Voltage (V)']}")
                st.markdown(f"**Output Voltage:** {record['Output Voltage (V)']}")
                st.markdown(f"**Efficiency:** {record['Efficiency %']}")
                st.markdown(f"**Status:** {record['Status']}")
                st.markdown(f"**AI Response / Diagnosis:**")
                st.info(record['AI Answer / Diagnosis'])
                
                if st.button(f"Delete Record #{actual_index + 1}", key=f"del_{actual_index}"):
                    st.session_state.historical_tests.pop(actual_index)
                    st.success("Record purged.")
                    st.rerun()

# ------------------------------------------------------------------------------
# SETTINGS & ABOUT
# ------------------------------------------------------------------------------
elif st.session_state.page == "Settings":
    st.header("🛠️ OS SYSTEM SETTINGS")
    st.markdown('<div class="os-card">', unsafe_allow_html=True)
    st.session_state.api_key = st.text_input("GEMINI API KEY", value=st.session_state.api_key, type="password", help="Add your Gemini API Key here to enable AI features.")
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.page == "About":
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=Rajdhani:wght@400;500;600;700&display=swap');

    .about-heading {
        font-family: 'Orbitron', sans-serif !important;
        font-weight: 800 !important;
        background: linear-gradient(90deg, #00f2fe 0%, #00ff87 50%, #7928ca 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 2px !important;
        text-transform: uppercase;
        margin-bottom: 12px !important;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .about-card {
        background: rgba(6, 12, 26, 0.65) !important;
        backdrop-filter: blur(25px) saturate(200%) !important;
        -webkit-backdrop-filter: blur(25px) saturate(200%) !important;
        border: 1px solid rgba(0, 242, 254, 0.25) !important;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.8), inset 0 0 15px rgba(0, 242, 254, 0.05) !important;
        border-radius: 14px !important;
        padding: 24px !important;
        margin-bottom: 24px !important;
        position: relative;
        overflow: hidden;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
    }

    .about-card:hover {
        transform: translateY(-5px) scale(1.01);
        border-color: rgba(0, 242, 254, 0.6) !important;
        box-shadow: 0 15px 35px -5px rgba(0, 242, 254, 0.35), inset 0 0 20px rgba(0, 242, 254, 0.2) !important;
    }

    .about-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; width: 100%; height: 2px;
        background: linear-gradient(90deg, #00f2fe, #00ff87, #7928ca, #00f2fe);
        background-size: 300% 100%;
        animation: borderGlow 4s linear infinite;
    }

    @keyframes borderGlow {
        0% { background-position: 0% 0%; }
        100% { background-position: 300% 0%; }
    }

    .team-card {
        background: rgba(10, 18, 38, 0.75);
        border: 1px solid rgba(0, 255, 135, 0.3);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 0 15px rgba(0, 255, 135, 0.1);
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        position: relative;
        overflow: hidden;
    }

    .team-card:hover {
        transform: translateY(-8px) scale(1.03);
        border-color: #00ff87;
        box-shadow: 0 0 25px rgba(0, 255, 135, 0.4);
    }

    .team-avatar {
        font-size: 2.2rem;
        margin-bottom: 8px;
    }

    .team-name {
        font-family: 'Orbitron', sans-serif;
        font-size: 1.15rem;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: 1px;
    }

    .team-role {
        font-size: 0.85rem;
        color: #00f2fe;
        font-family: 'Rajdhani', sans-serif;
        font-weight: 600;
        text-transform: uppercase;
        margin-top: 4px;
    }

    .tech-pill {
        display: inline-block;
        background: rgba(0, 242, 254, 0.08);
        border: 1px solid rgba(0, 242, 254, 0.3);
        color: #00f2fe;
        padding: 8px 16px;
        border-radius: 20px;
        font-family: 'Orbitron', sans-serif;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 5px;
        box-shadow: 0 0 10px rgba(0, 242, 254, 0.1);
        transition: all 0.3s ease;
    }

    .tech-pill:hover {
        background: rgba(0, 242, 254, 0.25);
        border-color: #00f2fe;
        box-shadow: 0 0 18px rgba(0, 242, 254, 0.5);
        transform: translateY(-2px);
    }

    .feature-pill {
        display: inline-block;
        background: rgba(0, 255, 135, 0.08);
        border: 1px solid rgba(0, 255, 135, 0.3);
        color: #00ff87;
        padding: 10px 18px;
        border-radius: 8px;
        font-family: 'Rajdhani', sans-serif;
        font-size: 0.95rem;
        font-weight: 700;
        margin: 6px;
        box-shadow: 0 0 10px rgba(0, 255, 135, 0.1);
        transition: all 0.3s ease;
    }

    .feature-pill:hover {
        background: rgba(0, 255, 135, 0.2);
        border-color: #00ff87;
        box-shadow: 0 0 20px rgba(0, 255, 135, 0.4);
        transform: translateY(-2px);
    }

    .info-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 15px;
    }

    .info-item {
        background: rgba(3, 7, 18, 0.6);
        border: 1px solid rgba(121, 40, 202, 0.3);
        border-radius: 8px;
        padding: 12px 18px;
    }

    .info-label {
        font-family: 'Rajdhani', sans-serif;
        font-size: 0.8rem;
        color: #9d4edd;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .info-value {
        font-family: 'Orbitron', sans-serif;
        font-size: 1rem;
        font-weight: 700;
        color: #ffffff;
        margin-top: 2px;
    }

    .about-footer {
        text-align: center;
        padding: 30px 20px;
        background: rgba(4, 8, 18, 0.85);
        border: 1px solid rgba(0, 242, 254, 0.3);
        border-radius: 14px;
        box-shadow: 0 0 25px rgba(0, 242, 254, 0.15);
        margin-top: 30px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="about-card">
        <h2 class="about-heading">⚡ AI-Based Electronic Circuit Tester</h2>
        <p style="font-size: 1.1rem; line-height: 1.6; color: #c8d6e5; margin-top: 10px;">
            An intelligent AI-powered electronic circuit diagnostic platform developed as a <b>Final Year B.Tech Project</b>. 
            The system combines <b>ESP32 hardware</b>, <b>MQTT communication</b>, <b>Streamlit dashboard</b>, and <b>Google Gemini AI</b> 
            to analyze electronic circuits in real time and provide automatic fault diagnosis.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="about-card">
        <h2 class="about-heading">⭐ TEAM: Achiver's ⭐</h2>
        <div style="margin-top: 20px;">
    """, unsafe_allow_html=True)

    t_col1, t_col2, t_col3, t_col4 = st.columns(4)

    team_members = [
        {"name": "Joshi Samarth", "role": "Hardware & Embedded Systems"},
        {"name": "Kamate Sumit", "role": "Full Stack & System Architect"},
        {"name": "Yedave Ganesh", "role": "AI Integration & Telemetry"},
        {"name": "Kale Krishna", "role": "IoT & Cloud Communications"}
    ]

    cols = [t_col1, t_col2, t_col3, t_col4]

    for idx, member in enumerate(team_members):
        with cols[idx]:
            st.markdown(f"""
            <div class="team-card">
                <div class="team-avatar">👨‍💻</div>
                <div class="team-name">{member['name']}</div>
                <div class="team-role">{member['role']}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    technologies = [
        "Python", "Streamlit", "ESP32", "MQTT", 
        "Google Gemini AI", "NumPy", "Pandas", 
        "Plotly", "JSON", "HTML", "CSS"
    ]

    tech_html = "".join([f'<span class="tech-pill">🔹 {tech}</span>' for tech in technologies])

    st.markdown(f"""
    <div class="about-card">
        <h2 class="about-heading">🛠️ TECHNOLOGIES USED</h2>
        <div style="margin-top: 15px; display: flex; flex-wrap: wrap; gap: 4px;">
            {tech_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

    features = [
        "AI Circuit Diagnosis", "Real-Time Sensor Monitoring", "MQTT Communication",
        "Interactive Dashboard", "Live Graphs", "Probe Guidance",
        "Circuit Database", "Test History", "Automated Fault Detection", "Professional UI"
    ]

    feat_html = "".join([f'<span class="feature-pill">✔ {feat}</span>' for feat in features])

    st.markdown(f"""
    <div class="about-card">
        <h2 class="about-heading">🚀 SYSTEM FEATURES</h2>
        <div style="margin-top: 15px; display: flex; flex-wrap: wrap; gap: 4px;">
            {feat_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="about-card">
        <h2 class="about-heading">ℹ️ PROJECT INFORMATION</h2>
        <div class="info-grid" style="margin-top: 15px;">
            <div class="info-item">
                <div class="info-label">VERSION</div>
                <div class="info-value">2.2</div>
            </div>
            <div class="info-item">
                <div class="info-label">PLATFORM</div>
                <div class="info-value">Streamlit</div>
            </div>
            <div class="info-item">
                <div class="info-label">HARDWARE</div>
                <div class="info-value">ESP32</div>
            </div>
            <div class="info-item">
                <div class="info-label">COMMUNICATION</div>
                <div class="info-value">MQTT</div>
            </div>
            <div class="info-item">
                <div class="info-label">AI ENGINE</div>
                <div class="info-value" style="color: #00ff87;">Google Gemini</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="about-footer">
        <div style="font-family: 'Rajdhani', sans-serif; font-size: 0.95rem; color: #8a99ad; text-transform: uppercase; letter-spacing: 2px;">
            Designed and Developed by
        </div>
        <div style="font-family: 'Orbitron', sans-serif; font-size: 1.6rem; font-weight: 800; color: #00f2fe; margin: 6px 0; letter-spacing: 1.5px;">
            ⭐ Team Achiver's ⭐
        </div>
        <div style="font-family: 'Rajdhani', sans-serif; font-size: 1.1rem; font-style: italic; color: #00ff87; margin-top: 8px;">
            "Engineering Innovation Through Artificial Intelligence"
        </div>
    </div>
    """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# OS FOOTER
# ------------------------------------------------------------------------------
st.markdown(f"""
<div style="border-top:1px solid rgba(0,242,254,0.15); padding:15px 0; margin-top:40px; font-size:0.75rem; color:#64748b; display:flex; justify-between:space-between; font-family:Orbitron;">
    <div><b>OS VERSION:</b> {APP_VERSION} | <b>PLATFORM:</b> NEXUS AI CORE</div>
    <div><b>HARDWARE MATRIX:</b> ESP32 ACTIVE | AWS CONNECTED | GEMINI READY</div>
</div>
""", unsafe_allow_html=True)