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
import uuid
import paho.mqtt.client as mqtt
import io
import html
import math
import re
import copy
import hashlib
import smtplib
import ssl
import socket
from email.message import EmailMessage
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

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
# 1. CONFIGURATION & CIRCUIT DATABASE (RECTIFIERS & DIGITAL CIRCUITS)
# ------------------------------------------------------------------------------
APP_NAME = "AI-Based Electronic Circuit Tester"
APP_VERSION = "2.3.0"
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
    "Digital Circuits": {
        "AND Gate": {
            "type": "logic_gate", "sub_type": "AND", "inputs": ["A", "B"], "outputs": ["Y"],
            "description": "Basic 2-input AND gate. Output is HIGH only if both inputs are HIGH.",
            "diagram": "Inputs A, B -> [ AND Gate ] -> Output Y = A & B",
            "probes": [{"step": 1, "name": "Input A", "loc": "Pin 1"}, {"step": 2, "name": "Input B", "loc": "Pin 2"}, {"step": 3, "name": "Output Y", "loc": "Pin 3"}]
        },
        "NAND Gate": {
            "type": "logic_gate", "sub_type": "NAND", "inputs": ["A", "B"], "outputs": ["Y"],
            "description": "Universal 2-input NAND gate. Output is LOW only if both inputs are HIGH.",
            "diagram": "Inputs A, B -> [ NAND Gate ] -> Output Y = ~(A & B)",
            "probes": [{"step": 1, "name": "Input A", "loc": "Pin 1"}, {"step": 2, "name": "Input B", "loc": "Pin 2"}, {"step": 3, "name": "Output Y", "loc": "Pin 3"}]
        },
        "OR Gate": {
            "type": "logic_gate", "sub_type": "OR", "inputs": ["A", "B"], "outputs": ["Y"],
            "description": "Basic 2-input OR gate. Output is HIGH if at least one input is HIGH.",
            "diagram": "Inputs A, B -> [ OR Gate ] -> Output Y = A | B",
            "probes": [{"step": 1, "name": "Input A", "loc": "Pin 1"}, {"step": 2, "name": "Input B", "loc": "Pin 2"}, {"step": 3, "name": "Output Y", "loc": "Pin 3"}]
        },
        "NOR Gate": {
            "type": "logic_gate", "sub_type": "NOR", "inputs": ["A", "B"], "outputs": ["Y"],
            "description": "Universal 2-input NOR gate. Output is HIGH only if both inputs are LOW.",
            "diagram": "Inputs A, B -> [ NOR Gate ] -> Output Y = ~(A | B)",
            "probes": [{"step": 1, "name": "Input A", "loc": "Pin 1"}, {"step": 2, "name": "Input B", "loc": "Pin 2"}, {"step": 3, "name": "Output Y", "loc": "Pin 3"}]
        },
        "XOR Gate": {
            "type": "logic_gate", "sub_type": "XOR", "inputs": ["A", "B"], "outputs": ["Y"],
            "description": "Exclusive-OR gate. Output is HIGH if inputs are different.",
            "diagram": "Inputs A, B -> [ XOR Gate ] -> Output Y = A ^ B",
            "probes": [{"step": 1, "name": "Input A", "loc": "Pin 1"}, {"step": 2, "name": "Input B", "loc": "Pin 2"}, {"step": 3, "name": "Output Y", "loc": "Pin 3"}]
        },
        "XNOR Gate": {
            "type": "logic_gate", "sub_type": "XNOR", "inputs": ["A", "B"], "outputs": ["Y"],
            "description": "Exclusive-NOR gate. Output is HIGH if inputs are identical.",
            "diagram": "Inputs A, B -> [ XNOR Gate ] -> Output Y = ~(A ^ B)",
            "probes": [{"step": 1, "name": "Input A", "loc": "Pin 1"}, {"step": 2, "name": "Input B", "loc": "Pin 2"}, {"step": 3, "name": "Output Y", "loc": "Pin 3"}]
        },
        "NOT Gate": {
            "type": "logic_gate", "sub_type": "NOT", "inputs": ["A"], "outputs": ["Y"],
            "description": "Inverter gate. Output is the logical negation of the input.",
            "diagram": "Input A -> [ NOT Gate ] -> Output Y = ~A",
            "probes": [{"step": 1, "name": "Input A", "loc": "Pin 1"}, {"step": 2, "name": "Output Y", "loc": "Pin 2"}]
        },
        "Binary-to-Gray Converter": {
            "type": "code_converter", "sub_type": "bin_to_gray", "inputs": ["configurable"], "outputs": ["configurable"],
            "description": "Converts binary code to Gray code (minimizing single-bit transition errors). Supports 2-bit, 3-bit, and 4-bit configurations.",
            "diagram": "Binary Bits (Bn...B0) -> [ XOR Network ] -> Gray Bits (Gn...G0)",
            "probes": [{"step": 1, "name": "Binary Inputs", "loc": "Bus A"}, {"step": 2, "name": "Gray Outputs", "loc": "Bus B"}]
        },
        "Gray-to-Binary Converter": {
            "type": "code_converter", "sub_type": "gray_to_bin", "inputs": ["configurable"], "outputs": ["configurable"],
            "description": "Converts Gray code back to standard binary code. Supports 2-bit, 3-bit, and 4-bit configurations.",
            "diagram": "Gray Bits (Gn...G0) -> [ Cumulative XOR ] -> Binary Bits (Bn...B0)",
            "probes": [{"step": 1, "name": "Gray Inputs", "loc": "Bus A"}, {"step": 2, "name": "Binary Outputs", "loc": "Bus B"}]
        },
        "Half Adder": {
            "type": "arithmetic", "sub_type": "half_adder", "inputs": ["A", "B"], "outputs": ["Sum", "Carry"],
            "description": "Adds two 1-bit binary numbers producing Sum and Carry outputs.",
            "diagram": "Inputs A, B -> [ Half Adder ] -> Sum (A^B), Carry (A & B)",
            "probes": [{"step": 1, "name": "Input A", "loc": "Pin A"}, {"step": 2, "name": "Input B", "loc": "Pin B"}, {"step": 3, "name": "Sum/Carry Outputs", "loc": "Pins S, C"}]
        },
        "Full Adder": {
            "type": "arithmetic", "sub_type": "full_adder", "inputs": ["A", "B", "Cin"], "outputs": ["Sum", "Carry-out"],
            "description": "Adds three 1-bit binary numbers including carry-in.",
            "diagram": "Inputs A, B, Cin -> [ Full Adder ] -> Sum, Carry-out",
            "probes": [{"step": 1, "name": "Inputs A, B, Cin", "loc": "Pins A, B, Cin"}, {"step": 2, "name": "Outputs", "loc": "Pins Sum, Cout"}]
        },
        "Half Subtractor": {
            "type": "arithmetic", "sub_type": "half_subtractor", "inputs": ["A", "B"], "outputs": ["Difference", "Borrow"],
            "description": "Subtracts one bit from another producing Difference and Borrow.",
            "diagram": "Inputs A, B -> [ Half Subtractor ] -> Difference (A^B), Borrow (~A & B)",
            "probes": [{"step": 1, "name": "Inputs A, B", "loc": "Pins A, B"}, {"step": 2, "name": "Outputs", "loc": "Pins Diff, Borrow"}]
        },
        "Full Subtractor": {
            "type": "arithmetic", "sub_type": "full_subtractor", "inputs": ["A", "B", "Bin"], "outputs": ["Difference", "Borrow-out"],
            "description": "Subtracts two bits and borrow-in producing Difference and Borrow-out.",
            "diagram": "Inputs A, B, Bin -> [ Full Subtractor ] -> Difference, Borrow-out",
            "probes": [{"step": 1, "name": "Inputs A, B, Bin", "loc": "Pins A, B, Bin"}, {"step": 2, "name": "Outputs", "loc": "Pins Diff, Bout"}]
        },
        "2:1 Multiplexer": {
            "type": "multiplexer", "sub_type": "mux_2_1", "inputs": ["S", "I0", "I1"], "outputs": ["Y"],
            "description": "Mandatory 2:1 MUX routing data input I0 or I1 to output Y based on select S. Boolean equation: Y = (~S & I0) | (S & I1).",
            "diagram": "Select S, Data I0, I1 -> [ 2:1 MUX ] -> Output Y = (~S & I0) | (S & I1)",
            "probes": [{"step": 1, "name": "Select S & Data I0, I1", "loc": "Pins S, I0, I1"}, {"step": 2, "name": "Output Y", "loc": "Pin Y"}]
        }
    }
}

# ==============================================================================
# MQTT COMMUNICATION MODULE (st.cache_resource-BACKED SINGLETON MANAGER)
# ==============================================================================
#
# ROOT CAUSE OF THE ORIGINAL BUG:
# Streamlit does not "import" this script once like a normal Python module --
# it re-executes the ENTIRE file, top to bottom, on every single rerun
# (every button click, every widget interaction, every st.rerun()). That
# means plain module-level globals such as the old
#     _mqtt_client = None
#     _mqtt_started = False
#     _latest_mqtt_packet = None
#     _mqtt_status = "Disconnected"
#     _mqtt_packet_count = 0
# were being RESET TO THEIR DEFAULTS on every rerun. Because _mqtt_started
# flipped back to False each time, initialize_mqtt() kept thinking no client
# existed yet and spun up a BRAND NEW mqtt.Client + a brand new loop_start()
# background thread on every rerun -- while the client(s) from earlier
# reruns kept running in the background too (never stopped), silently
# continuing to receive packets into globals that the current script
# execution can no longer see. The UI, reading the freshly-reset
# "_latest_mqtt_packet = None" of *this* rerun, showed "WAITING FOR DATA"
# even though a packet had already arrived (into an orphaned older
# instance's state).
#
# THE FIX: move all MQTT state (client, lock, latest packet, counters,
# connection status) into a single object that is created ONCE per Python
# process -- not once per script run -- using st.cache_resource. Every
# read and write goes through that one persistent object, so reruns can
# no longer wipe out or duplicate MQTT state.
# ==============================================================================
MQTT_BROKER_HOST = "broker.hivemq.com"
MQTT_BROKER_PORT = 1883
MQTT_TOPIC = "circuit/tester"
MQTT_KEEPALIVE = 60

# ESP32 is considered ONLINE only while valid telemetry keeps arriving. If no
# valid packet has arrived for this many seconds, the ESP32 is shown OFFLINE.
# (Independent of the MQTT broker connection state.) Easy to change.
ESP32_OFFLINE_TIMEOUT = 10

# Fallback transport: MQTT-over-WebSockets. Used automatically if plain
# TCP on MQTT_BROKER_PORT doesn't connect within a few seconds -- see
# _mqtt_fallback_watchdog(). Port 8000 is HiveMQ's public unencrypted
# WebSocket listener.
MQTT_WS_PORT = 8000
MQTT_WS_PATH = "/mqtt"

# Mandatory fields (after alias normalization) required for a packet to be
# considered valid for diagnosis.
MQTT_REQUIRED_FIELDS = ["input_voltage", "output_voltage", "input_current", "output_current"]

# Canonical field name -> accepted raw JSON key aliases.
MQTT_FIELD_ALIASES = {
    "input_voltage":  ["input_voltage", "input_v"],
    "output_voltage": ["output_voltage", "output_v"],
    "input_current":  ["input_current", "input_i"],
    "output_current": ["output_current", "output_i"],
    "frequency":      ["frequency", "freq"],
    "temperature":    ["temperature", "temp"],
}


class MQTTManager:
    """Thread-safe, process-persistent MQTT state container. Exactly one
    instance of this class exists for the life of the Streamlit process
    (see get_mqtt_manager() below)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.client = None
        self.client_id = f"nexus_streamlit_{uuid.uuid4().hex[:12]}"
        self.started = False

        # Pure MQTT broker CONNECTION state -- set only by on_connect/on_disconnect.
        self.connection_status = "Disconnected"   # "Connected" | "Disconnected"

        # Pure DATA state -- set only by on_message. This is a DIFFERENT
        # concept from connection_status: you can be connected with no
        # data yet, or (briefly) still holding good data while reconnecting.
        self.latest_packet = None        # normalized dict, or None
        self.latest_raw_packet = None    # raw payload dict, for debugging
        self.packet_count = 0
        self.last_packet_time = None
        self.last_packet_topic = None

        # Diagnostics: WHY it's disconnected, if it is. This is what was
        # previously invisible -- print(...) only reaches server-side
        # logs, never the Streamlit UI itself, so a genuine connection
        # failure (e.g. an outbound port being blocked by the hosting
        # platform) looked identical to "no data yet" with no way to
        # tell them apart from inside the app.
        self.last_error = None
        self.transport = "tcp"          # "tcp" | "websockets"
        self.connect_attempt_time = None
        self.fallback_attempted = False


@st.cache_resource
def get_mqtt_manager():
    """Returns the single MQTTManager instance for this process. Because
    it's wrapped in st.cache_resource, Streamlit hands back the SAME
    object on every rerun instead of constructing a fresh one."""
    return MQTTManager()


def normalize_mqtt_packet(raw):
    """
    Normalize a raw MQTT JSON payload into the canonical field set
    (input_voltage, output_voltage, input_current, output_current,
    frequency, temperature), accepting both the full field names and the
    short aliases (input_v/output_v/input_i/output_i) already used
    elsewhere in this app.

    Returns None if `raw` isn't a dict or is missing any mandatory
    diagnostic field. Optional fields (frequency/temperature) default to
    0.0 rather than causing rejection.
    """
    if not isinstance(raw, dict):
        return None

    normalized = {}
    for canonical, aliases in MQTT_FIELD_ALIASES.items():
        for key in aliases:
            if key in raw and raw[key] is not None:
                try:
                    normalized[canonical] = float(raw[key])
                except (TypeError, ValueError):
                    continue
                break

    if not all(field in normalized for field in MQTT_REQUIRED_FIELDS):
        return None

    normalized.setdefault("frequency", 0.0)
    normalized.setdefault("temperature", 0.0)
    return normalized


# ------------------------------------------------------------------------
# CONNACK reason lookup for readable error messages (v3.1.1 codes; Paho
# also accepts these for v5 ints in VERSION1 compatibility mode).
# ------------------------------------------------------------------------
MQTT_CONNACK_REASONS = {
    1: "Connection refused - incorrect protocol version",
    2: "Connection refused - invalid client identifier",
    3: "Connection refused - server unavailable",
    4: "Connection refused - bad username or password",
    5: "Connection refused - not authorised",
}

def _is_int_like(value):
    try:
        int(value)
        return True
    except (TypeError, ValueError):
        return False


# ------------------------------------------------------------------------
# Paho callbacks. These run on the MQTT network thread -- they must ONLY
# touch the thread-safe manager, never Streamlit UI calls.
# ------------------------------------------------------------------------
def on_connect(client, userdata, flags, rc, properties=None):
    manager = userdata
    # rc may be an int (VERSION1 API) or a ReasonCode-like object; both
    # compare equal to 0 on success, and str()/int() give a readable value
    # for the "connection refused" reasons either way.
    if rc == 0:
        print("MQTT CONNECTED", flush=True)
        with manager.lock:
            manager.connection_status = "Connected"
            manager.last_error = None
        client.subscribe(MQTT_TOPIC)
        print(f"MQTT SUBSCRIBED [{MQTT_TOPIC}]", flush=True)
    else:
        reason = MQTT_CONNACK_REASONS.get(int(rc), f"Unknown reason code {rc}") if _is_int_like(rc) else str(rc)
        print(f"MQTT CONNECTION ERROR: {rc} ({reason})", flush=True)
        with manager.lock:
            manager.connection_status = "Disconnected"
            manager.last_error = f"Broker refused connection: {reason}"

def on_disconnect(client, userdata, rc, properties=None):
    manager = userdata
    print(f"MQTT DISCONNECTED: {rc}", flush=True)
    with manager.lock:
        manager.connection_status = "Disconnected"
        if rc != 0:
            manager.last_error = f"Disconnected unexpectedly (rc={rc}). Broker/network dropped the connection."

def on_message(client, userdata, msg):
    manager = userdata
    try:
        payload_str = msg.payload.decode("utf-8")
        data = json.loads(payload_str)
        normalized = normalize_mqtt_packet(data)

        if normalized is not None:
            with manager.lock:
                manager.latest_packet = normalized
                manager.latest_raw_packet = data if isinstance(data, dict) else None
                manager.packet_count += 1
                manager.last_packet_time = datetime.datetime.now()
                manager.last_packet_topic = msg.topic
            print(f"MQTT MESSAGE [{msg.topic}]: {payload_str}", flush=True)
        else:
            # Malformed/incomplete payload: log it, but deliberately do
            # NOT touch manager.latest_packet -- a previously received
            # valid packet must never be wiped out by a bad payload.
            print(f"MQTT MESSAGE IGNORED (missing required fields) [{msg.topic}]: {payload_str}", flush=True)
    except json.JSONDecodeError as e:
        print(f"MQTT JSON ERROR: {e}", flush=True)
    except Exception as e:
        print(f"MQTT MESSAGE ERROR: {e}", flush=True)


def initialize_mqtt():
    """
    Singleton initializer for the MQTT client, backed by the persistent
    MQTTManager. Guarantees only one client and one loop_start() thread
    ever exist for the life of the process, no matter how many times
    Streamlit reruns this script. Non-blocking: reconnection is handled
    natively by Paho's loop_start() thread + reconnect_delay_set().

    Also starts a background watchdog that automatically retries over
    MQTT-over-WebSockets if plain TCP hasn't connected within a few
    seconds -- see _mqtt_fallback_watchdog() for why this matters.
    """
    manager = get_mqtt_manager()

    with manager.lock:
        if manager.started and manager.client is not None:
            return
        manager.started = True

    print("MQTT CONNECTING (tcp)", flush=True)
    try:
        client = _create_mqtt_client(manager, transport="tcp")
        _connect_client(client, "tcp")

        with manager.lock:
            manager.client = client
            manager.transport = "tcp"
            manager.connect_attempt_time = datetime.datetime.now()

        watchdog = threading.Thread(target=_mqtt_fallback_watchdog, args=(manager,), daemon=True)
        watchdog.start()
    except Exception as e:
        print(f"MQTT CONNECTION ERROR: {e}", flush=True)
        with manager.lock:
            manager.connection_status = "Disconnected"
            manager.last_error = f"Failed to start MQTT client: {e}"
            manager.started = False


def _create_mqtt_client(manager, transport="tcp"):
    try:
        # Compatible with Paho MQTT v2.x
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=manager.client_id, transport=transport)
    except AttributeError:
        # Fallback for Paho MQTT v1.x
        client = mqtt.Client(client_id=manager.client_id, transport=transport)

    if transport == "websockets":
        client.ws_set_options(path=MQTT_WS_PATH)

    # Bind our persistent manager as the callback userdata so on_connect/
    # on_disconnect/on_message can update it without touching globals.
    client.user_data_set(manager)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    if hasattr(client, "reconnect_delay_set"):
        client.reconnect_delay_set(min_delay=1, max_delay=10)

    return client


def _connect_client(client, transport):
    port = MQTT_BROKER_PORT if transport == "tcp" else MQTT_WS_PORT
    client.connect_async(MQTT_BROKER_HOST, port, MQTT_KEEPALIVE)
    client.loop_start()


def _mqtt_fallback_watchdog(manager, timeout_seconds=8):
    """
    Runs once per process on a background thread. If the initial plain-TCP
    MQTT connection (port 1883) hasn't succeeded within `timeout_seconds`,
    automatically retries over MQTT-over-WebSockets (port 8000).

    WHY THIS MATTERS: raw TCP on a non-standard port like 1883 is exactly
    the kind of outbound connection many hosting platforms (Streamlit
    Community Cloud, various container/PaaS platforms, restrictive
    corporate networks) silently block or drop -- Paho just keeps retrying
    forever with no error raised, which from inside the app looks
    identical to "the code never connects". If you deployed this app to a
    platform like that, this is almost certainly why MQTT STATUS shows
    DISCONNECTED even though your ESP32 is publishing fine. WebSockets on
    port 8000 rides over a normal HTTP-style connection and is far less
    likely to be blocked.
    """
    time.sleep(timeout_seconds)
    with manager.lock:
        already_connected = manager.connection_status == "Connected"
        already_tried = manager.fallback_attempted
        old_client = manager.client

    if already_connected or already_tried:
        return

    print(f"MQTT TCP CONNECT TIMED OUT after {timeout_seconds}s -- retrying over WebSockets (port {MQTT_WS_PORT})", flush=True)
    try:
        if old_client is not None:
            try:
                old_client.loop_stop()
                old_client.disconnect()
            except Exception:
                pass

        ws_client = _create_mqtt_client(manager, transport="websockets")
        _connect_client(ws_client, "websockets")

        with manager.lock:
            manager.client = ws_client
            manager.transport = "websockets"
            manager.fallback_attempted = True
            manager.connect_attempt_time = datetime.datetime.now()
            if manager.connection_status != "Connected":
                manager.last_error = (
                    f"Plain TCP MQTT (port {MQTT_BROKER_PORT}) did not connect within "
                    f"{timeout_seconds}s -- likely blocked by the hosting network/firewall. "
                    f"Retrying now over MQTT-over-WebSockets (port {MQTT_WS_PORT})."
                )
    except Exception as e:
        print(f"MQTT WEBSOCKET FALLBACK ERROR: {e}", flush=True)
        with manager.lock:
            manager.fallback_attempted = True
            manager.last_error = f"TCP connect timed out, and WebSocket fallback also failed: {e}"


def get_mqtt_connection_status():
    """Pure broker connection truth: 'Connected' or 'Disconnected'.
    Never conflated with whether a data packet has arrived."""
    manager = get_mqtt_manager()
    with manager.lock:
        return manager.connection_status


def get_mqtt_last_error():
    """Human-readable reason for the current disconnected state, or None
    if connected / not yet known. Surfaced in the UI debug panel since
    print() output alone is invisible once the app is deployed."""
    manager = get_mqtt_manager()
    with manager.lock:
        return manager.last_error


def get_mqtt_transport():
    manager = get_mqtt_manager()
    with manager.lock:
        return manager.transport


def get_mqtt_data_status():
    """Pure data truth: 'Packet Received' or 'Waiting for Data'."""
    manager = get_mqtt_manager()
    with manager.lock:
        return "Packet Received" if manager.latest_packet is not None else "Waiting for Data"


def get_mqtt_status():
    """
    Backward-compatible combined status consumed by the existing UI code:
      'Connected'         -> broker connected AND a valid packet received
      'Waiting for Data'   -> broker connected, no valid packet yet
      'Disconnected'       -> broker not connected
    Connection state and data state are tracked separately internally
    (see get_mqtt_connection_status / get_mqtt_data_status) and only
    combined here for display purposes.
    """
    manager = get_mqtt_manager()
    with manager.lock:
        if manager.connection_status != "Connected":
            return "Disconnected"
        if manager.latest_packet is None:
            return "Waiting for Data"
        return "Connected"


def get_mqtt_packet_count():
    manager = get_mqtt_manager()
    with manager.lock:
        return manager.packet_count


def get_mqtt_last_packet_time():
    manager = get_mqtt_manager()
    with manager.lock:
        return manager.last_packet_time


def get_mqtt_last_topic():
    manager = get_mqtt_manager()
    with manager.lock:
        return manager.last_packet_topic


def get_latest_sensor_packet():
    """Returns a COPY of the latest normalized, validated sensor packet, or
    None if no valid packet has been received yet. Backed by the
    cache_resource-persisted MQTTManager, so a valid packet survives
    Streamlit reruns instead of being reset to None."""
    manager = get_mqtt_manager()
    with manager.lock:
        if manager.latest_packet is None:
            return None
        return dict(manager.latest_packet)


def get_latest_raw_packet():
    """Returns a COPY of the last raw (pre-normalization) packet payload,
    for the debug panel."""
    manager = get_mqtt_manager()
    with manager.lock:
        if manager.latest_raw_packet is None:
            return None
        return dict(manager.latest_raw_packet)

def get_latest_packet_and_time():
    """Atomically returns (copy of latest valid packet or None, its arrival
    datetime or None) so the pair can never be mismatched."""
    manager = get_mqtt_manager()
    with manager.lock:
        if manager.latest_packet is None:
            return None, None
        return dict(manager.latest_packet), manager.last_packet_time


def get_esp32_status():
    """
    ESP32 online state, derived ONLY from the age of the last valid telemetry
    packet (never from the MQTT broker connection state):
      ("ONLINE",  age_seconds)  valid packet within ESP32_OFFLINE_TIMEOUT
      ("OFFLINE", age_seconds)  last valid packet is older than the timeout
      ("WAITING", None)         broker connected, no valid packet received yet
      ("OFFLINE", None)         no valid packet ever and broker not connected
    """
    manager = get_mqtt_manager()
    with manager.lock:
        last_time = manager.last_packet_time
        broker_connected = manager.connection_status == "Connected"
    if last_time is None:
        return ("WAITING", None) if broker_connected else ("OFFLINE", None)
    age = (datetime.datetime.now() - last_time).total_seconds()
    if age <= ESP32_OFFLINE_TIMEOUT:
        return "ONLINE", age
    return "OFFLINE", age


def validate_sensor_packet(raw):
    """Returns the list of required electrical fields that are missing or
    non-finite in `raw`. Empty list == all four measurements present."""
    missing = []
    for field in MQTT_REQUIRED_FIELDS:
        try:
            ok = raw is not None and raw.get(field) is not None and math.isfinite(float(raw[field]))
        except (TypeError, ValueError):
            ok = False
        if not ok:
            missing.append(field)
    return missing

# ------------------------------------------------------------------------------
# DIGITAL CIRCUIT TRUTH TABLE GENERATORS & LOGIC THRESHOLDS
# ------------------------------------------------------------------------------
def classify_digital_voltage(voltage, v_il=0.8, v_ih=2.0):
    """Classifies measured voltage into logic 0, logic 1, or INVALID based on thresholds."""
    try:
        v = float(voltage)
        if not math.isfinite(v):
            return "INVALID"
        if v <= v_il:
            return "0"
        elif v >= v_ih:
            return "1"
        else:
            return "INVALID"
    except (TypeError, ValueError):
        return "INVALID"

def generate_expected_truth_table(circuit_name, width=4):
    """Programmatically generates expected truth tables for all supported digital circuits."""
    ckt = CIRCUIT_DATABASE.get("Digital Circuits", {}).get(circuit_name, {})
    stype = ckt.get("sub_type")
    
    rows = []
    if stype == "AND":
        for a in [0, 1]:
            for b in [0, 1]:
                rows.append({"Inputs": f"A={a}, B={b}", "A": a, "B": b, "Expected Y": a & b})
    elif stype == "NAND":
        for a in [0, 1]:
            for b in [0, 1]:
                rows.append({"Inputs": f"A={a}, B={b}", "A": a, "B": b, "Expected Y": 1 if not (a & b) else 0})
    elif stype == "OR":
        for a in [0, 1]:
            for b in [0, 1]:
                rows.append({"Inputs": f"A={a}, B={b}", "A": a, "B": b, "Expected Y": a | b})
    elif stype == "NOR":
        for a in [0, 1]:
            for b in [0, 1]:
                rows.append({"Inputs": f"A={a}, B={b}", "A": a, "B": b, "Expected Y": 1 if not (a | b) else 0})
    elif stype == "XOR":
        for a in [0, 1]:
            for b in [0, 1]:
                rows.append({"Inputs": f"A={a}, B={b}", "A": a, "B": b, "Expected Y": a ^ b})
    elif stype == "XNOR":
        for a in [0, 1]:
            for b in [0, 1]:
                rows.append({"Inputs": f"A={a}, B={b}", "A": a, "B": b, "Expected Y": 0 if (a ^ b) else 1})
    elif stype == "NOT":
        for a in [0, 1]:
            rows.append({"Inputs": f"A={a}", "A": a, "Expected Y": 0 if a else 1})
    elif stype == "bin_to_gray":
        n = width
        for i in range(2**n):
            b_bits = [(i >> (n - 1 - k)) & 1 for k in range(n)]
            g_val = i ^ (i >> 1)
            g_bits = [(g_val >> (n - 1 - k)) & 1 for k in range(n)]
            input_label = "".join(str(b) for b in b_bits)
            row = {"Input": input_label}
            for k in range(n):
                row[f"B{n-1-k}"] = b_bits[k]
            for k in range(n):
                row[f"Expected G{n-1-k}"] = g_bits[k]
            rows.append(row)
    elif stype == "gray_to_bin":
        n = width
        for i in range(2**n):
            g_bits = [(i >> (n - 1 - k)) & 1 for k in range(n)]
            b_val = 0
            for k in range(n):
                b_val ^= (i >> k)
            b_bits = [(b_val >> (n - 1 - k)) & 1 for k in range(n)]
            input_label = "".join(str(g) for g in g_bits)
            row = {"Input": input_label}
            for k in range(n):
                row[f"G{n-1-k}"] = g_bits[k]
            for k in range(n):
                row[f"Expected B{n-1-k}"] = b_bits[k]
            rows.append(row)
    elif stype == "half_adder":
        for a in [0, 1]:
            for b in [0, 1]:
                s = a ^ b
                c = a & b
                rows.append({"A": a, "B": b, "Expected Sum": s, "Expected Carry": c})
    elif stype == "full_adder":
        for a in [0, 1]:
            for b in [0, 1]:
                for cin in [0, 1]:
                    s = a ^ b ^ cin
                    cout = (a & b) | (cin & (a ^ b))
                    rows.append({"A": a, "B": b, "Cin": cin, "Expected Sum": s, "Expected Carry-out": cout})
    elif stype == "half_subtractor":
        for a in [0, 1]:
            for b in [0, 1]:
                diff = a ^ b
                borrow = (not a) & b
                rows.append({"A": a, "B": b, "Expected Difference": diff, "Expected Borrow": 1 if borrow else 0})
    elif stype == "full_subtractor":
        for a in [0, 1]:
            for b in [0, 1]:
                for bin_val in [0, 1]:
                    diff = a ^ b ^ bin_val
                    borrow = ((not a) & b) | ((not (a ^ b)) & bin_val)
                    rows.append({"A": a, "B": b, "Bin": bin_val, "Expected Difference": diff, "Expected Borrow-out": 1 if borrow else 0})
    elif stype == "mux_2_1":
        for s in [0, 1]:
            for i0 in [0, 1]:
                for i1 in [0, 1]:
                    y = ((not s) & i0) | (s & i1)
                    rows.append({"S": s, "I0": i0, "I1": i1, "Expected Y": 1 if y else 0})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------
# DIGITAL TESTER HELPERS (cell selection, fresh-measurement capture, analysis)
# ------------------------------------------------------------------------------
def get_digital_table_layout(expected_df):
    """Splits the expected truth table into input columns, output columns and
    output labels using the same rule the digital tester has always used."""
    output_cols = [c for c in expected_df.columns if c.startswith("Expected ") or c in ["Y", "Sum", "Carry", "Carry-out", "Difference", "Borrow", "Borrow-out"]]
    input_cols = [c for c in expected_df.columns if c not in output_cols]
    possible_outputs = [c.replace("Expected ", "") for c in output_cols]
    return input_cols, output_cols, possible_outputs


def get_fresh_output_measurement():
    """Returns (voltage, packet_time, error_message). Only a genuine, recent,
    fully valid telemetry packet yields a voltage; otherwise voltage is None
    and an error message explains why. Never fabricates a zero."""
    packet, packet_time = get_latest_packet_and_time()
    if packet is None or packet_time is None:
        return None, None, "No valid sensor telemetry packet has been received yet."
    age = (datetime.datetime.now() - packet_time).total_seconds()
    if age > ESP32_OFFLINE_TIMEOUT:
        return None, packet_time, f"Latest sensor packet is stale ({age:.1f} s old, limit {ESP32_OFFLINE_TIMEOUT} s). ESP32 appears offline."
    missing = validate_sensor_packet(packet)
    if missing:
        return None, packet_time, "Latest sensor packet is incomplete (missing/invalid: " + ", ".join(missing) + ")."
    try:
        voltage = float(packet.get("output_voltage", packet.get("output_v")))
    except (TypeError, ValueError):
        return None, packet_time, "Latest sensor packet has no usable output voltage."
    if not math.isfinite(voltage):
        return None, packet_time, "Latest sensor packet has a non-finite output voltage."
    return voltage, packet_time, None


def digital_table_signature(expected_df):
    return (len(expected_df), tuple(str(c) for c in expected_df.columns))


def digital_invalidate_analysis(circuit_name):
    """Drops the stored analysis (deterministic result + Gemini report) of one circuit only."""
    st.session_state.digital_analysis.pop(circuit_name, None)


def digital_select_cell(circuit_name, row_idx, out_label):
    """on_click callback for a truth-table cell button: changes only the active destination."""
    st.session_state.digital_selected_cells[circuit_name] = (row_idx, out_label)
    st.session_state.digital_save_notice.pop(circuit_name, None)


def compute_digital_analysis(circuit_name, expected_df, measurements):
    """Deterministic comparison of saved measurements with the expected truth table."""
    input_cols, output_cols, possible_outputs = get_digital_table_layout(expected_df)
    total = len(expected_df) * len(possible_outputs)
    valid = invalid = mismatches = 0
    details = []
    cells = []
    for i in range(len(expected_df)):
        inputs_txt = ", ".join(f"{c}={expected_df.iloc[i][c]}" for c in input_cols)
        for out_l in possible_outputs:
            exp_col = f"Expected {out_l}" if f"Expected {out_l}" in expected_df.columns else out_l
            exp_val = int(expected_df.iloc[i][exp_col])
            m = measurements.get((i, out_l))
            if m is None:
                status_c, v_txt, state_c = "MISSING", "\u2014", "MISSING"
            else:
                try:
                    v_txt = f"{float(m['voltage']):.3f} V"
                except (TypeError, ValueError):
                    v_txt = "N/A"
                if m.get("logic_state") in ("0", "1"):
                    valid += 1
                    state_c = m["logic_state"]
                    if int(state_c) == exp_val:
                        status_c = "MATCH"
                    else:
                        status_c = "MISMATCH"
                        mismatches += 1
                else:
                    invalid += 1
                    state_c, status_c = "INVALID", "INVALID"
            cells.append({"row": i, "inputs": inputs_txt, "output": out_l, "expected": exp_val,
                          "voltage": v_txt, "state": state_c, "status": status_c})
            if status_c != "MATCH":
                details.append({"Row": i, "Inputs": inputs_txt, "Output": out_l, "Expected": exp_val,
                                "Measured V": v_txt, "Measured State": state_c, "Status": status_c})
    missing = total - valid - invalid
    coverage = (valid / total * 100.0) if total > 0 else 0.0
    if total == 0 or missing > 0 or invalid > 0:
        status = "INCOMPLETE"
    elif mismatches > 0:
        status = "FAIL"
    else:
        status = "PASS"
    return {
        "circuit": circuit_name,
        "signature": digital_table_signature(expected_df),
        "det_status": status,
        "coverage_pct": coverage,
        "total_cells": total,
        "valid_cells": valid,
        "correct_matches": valid - mismatches,
        "mismatches": mismatches,
        "missing_cells": missing,
        "invalid_cells": invalid,
        "details": details,
        "cells": cells,
        "thresholds": dict(st.session_state.digital_thresholds),
        "analysed_at": datetime.datetime.now(),
        "gemini_report": None,
        "gemini_status": "NOT_RUN",
        "gemini_error": None,
    }


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

    # HOLD / RELEASE snapshot state (UI-only; never touches MQTTManager)
    if "data_hold" not in st.session_state:
        st.session_state.data_hold = False
    # INPUT-ONLY hold: {"input_v", "input_i", "captured_at", "circuit"}.
    # Never contains output voltage/current, frequency or temperature.
    if "held_input_data" not in st.session_state:
        st.session_state.held_input_data = None
    if "hold_timestamp" not in st.session_state:
        st.session_state.hold_timestamp = None
    if "hold_error" not in st.session_state:
        st.session_state.hold_error = None
    # Last successful Gemini analysis (+ the exact snapshot it analysed)
    if "last_gemini_result" not in st.session_state:
        st.session_state.last_gemini_result = None
        
    # Target value session state definitions
    if "target_input_voltage" not in st.session_state:
        st.session_state.target_input_voltage = None
    if "target_output_voltage" not in st.session_state:
        st.session_state.target_output_voltage = None
    if "target_input_current" not in st.session_state:
        st.session_state.target_input_current = None
    if "target_output_current" not in st.session_state:
        st.session_state.target_output_current = None

    # Digital testing state variables
    if "digital_measurements" not in st.session_state:
        st.session_state.digital_measurements = {}
    if "digital_selected_cell" not in st.session_state:
        st.session_state.digital_selected_cell = (0, 0)
    if "digital_bit_width" not in st.session_state:
        st.session_state.digital_bit_width = 4
    if "digital_thresholds" not in st.session_state:
        st.session_state.digital_thresholds = {"v_il": 0.8, "v_ih": 2.0}
    if "digital_selected_cells" not in st.session_state:
        st.session_state.digital_selected_cells = {}
    if "digital_analysis" not in st.session_state:
        st.session_state.digital_analysis = {}
    if "digital_save_notice" not in st.session_state:
        st.session_state.digital_save_notice = {}
    if "digital_table_sigs" not in st.session_state:
        st.session_state.digital_table_sigs = {}
    if "analysis_records" not in st.session_state:
        st.session_state.analysis_records = []
    if "student_details" not in st.session_state:
        st.session_state.student_details = {}
    if "report_state" not in st.session_state:
        st.session_state.report_state = None
    if "report_selected_test" not in st.session_state:
        st.session_state.report_selected_test = None
    if "report_validate_attempted" not in st.session_state:
        st.session_state.report_validate_attempted = False

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
    packet, packet_time = get_latest_packet_and_time()
    data = build_sensor_data(packet, circuit_info)
    data["packet_time"] = packet_time
    return data

def build_sensor_data(packet, circuit_info):
    active_targets = get_active_targets(circuit_info)
    if packet is not None:
        meas_in = float(packet.get("input_voltage", packet.get("input_v", 0)))
        meas_out = float(packet.get("output_voltage", packet.get("output_v", 0)))
        meas_in_i = float(packet.get("input_current", packet.get("input_i", 0)))
        meas_out_i = float(packet.get("output_current", packet.get("output_i", 0)))
        temp = float(packet.get("temperature", 0))
        freq = float(packet.get("frequency", 0))
    else:
        meas_in = 0.0
        meas_out = 0.0
        meas_in_i = 0.0
        meas_out_i = 0.0
        temp = 0.0
        freq = 0.0

    p_in = meas_in * meas_in_i
    p_out = meas_out * meas_out_i
    eff = (p_out / p_in * 100.0) if p_in > 0 else 0.0
    v_drop = max(0.0, meas_in - meas_out)

    v_dev = abs(meas_out - active_targets["target_output_voltage"]) / active_targets["target_output_voltage"] if active_targets["target_output_voltage"] > 0 else 0
    health = max(0, min(100, int((1.0 - v_dev) * 100)))

    return {
        "input_v": meas_in, "output_v": meas_out,
        "input_i": meas_in_i, "output_i": meas_out_i,
        "power_in": round(p_in, 2), "power_out": round(p_out, 2),
        "efficiency": round(eff, 2), "v_drop": round(v_drop, 2),
        "temperature": temp, "frequency": freq, "health": health
    }

# ------------------------------------------------------------------------------
# HOLD / RELEASE (UI snapshot only -- MQTT keeps receiving in the background)
# ------------------------------------------------------------------------------
def hold_testing_data():
    packet, _packet_time = get_latest_packet_and_time()
    if packet is None:
        st.session_state.hold_error = "No valid sensor data available to hold."
        return
    try:
        measured_input_voltage = float(packet.get("input_voltage", packet.get("input_v")))
        measured_input_current = float(packet.get("input_current", packet.get("input_i")))
        if not (math.isfinite(measured_input_voltage) and math.isfinite(measured_input_current)):
            raise ValueError("non-finite input measurement")
    except (TypeError, ValueError):
        st.session_state.hold_error = "Input voltage/current missing from the latest packet - nothing held."
        return
    captured_at = datetime.datetime.now()
    st.session_state.held_input_data = {
        "input_v": measured_input_voltage,
        "input_i": measured_input_current,
        "captured_at": captured_at,
        "circuit": st.session_state.selected_circuit,
    }
    st.session_state.hold_timestamp = captured_at
    st.session_state.data_hold = True
    st.session_state.hold_error = None

def release_testing_data():
    st.session_state.data_hold = False
    st.session_state.held_input_data = None
    st.session_state.hold_timestamp = None
    st.session_state.hold_error = None

def is_data_held():
    return bool(st.session_state.get("data_hold")) and st.session_state.get("held_input_data") is not None

def merge_held_input(packet):
    merged = dict(packet) if packet is not None else {}
    if is_data_held():
        held = st.session_state.held_input_data
        merged["input_voltage"] = held["input_v"]
        merged["input_current"] = held["input_i"]
        merged["input_v"] = held["input_v"]
        merged["input_i"] = held["input_i"]
    return merged

def get_testing_sensor_data(circuit_info):
    if is_data_held():
        packet, packet_time = get_latest_packet_and_time()
        data = build_sensor_data(merge_held_input(packet), circuit_info)
        data["packet_time"] = packet_time
        data["captured_at"] = st.session_state.held_input_data["captured_at"]
        data["source"] = "HELD"
        return data
    data = get_live_sensor_data(circuit_info)
    data["source"] = "LIVE"
    return data

# ------------------------------------------------------------------------------
# NEXUS TELEMETRY: HELD INPUT (V, I)  vs  LIVE OUTPUT (V, I)
# ------------------------------------------------------------------------------
def compute_power_efficiency(v_in, i_in, v_out, i_out):
    p_in = float(v_in) * float(i_in)
    p_out = float(v_out) * float(i_out)
    eff = (p_out / p_in * 100.0) if p_in > 1e-9 else None
    return p_in, p_out, eff


def generate_waveform_chart(freq_val, v_in, v_out, i_in=0.0, i_out=0.0, input_held=False):
    f_draw = freq_val if (freq_val is not None and freq_val > 0) else 50.0
    t = np.linspace(0, 0.04, 500)
    s = np.sin(2 * np.pi * f_draw * t)

    in_tag = "HELD" if input_held else "LIVE"
    in_col = "#ffb703" if input_held else "#00f2fe"
    out_v_col, out_i_col = "#00ff87", "#9d4edd"

    fig = make_subplots(
        rows=2, cols=2, shared_xaxes=True, vertical_spacing=0.20, horizontal_spacing=0.07,
        subplot_titles=(
            f"{in_tag} INPUT VOLTAGE  ({v_in:.2f} V)",
            f"LIVE OUTPUT VOLTAGE  ({v_out:.2f} V)",
            f"{in_tag} INPUT CURRENT  ({i_in:.3f} A)",
            f"LIVE OUTPUT CURRENT  ({i_out:.3f} A)",
        ))
    fig.update_annotations(font=dict(size=11, color="#c8d6e5"))

    fig.add_trace(go.Scatter(x=t, y=v_in * s, mode="lines", name=f"{in_tag} Input V(t)",
                             line=dict(color=in_col, width=3)), row=1, col=1)
    fig.add_trace(go.Scatter(x=t, y=np.abs(v_out * s), mode="lines", name="LIVE Output V(t)",
                             line=dict(color=out_v_col, width=3)), row=1, col=2)
    fig.add_trace(go.Scatter(x=t, y=i_in * s, mode="lines", name=f"{in_tag} Input I(t)",
                             line=dict(color=in_col, width=3, dash="dot")), row=2, col=1)
    fig.add_trace(go.Scatter(x=t, y=np.abs(i_out * s), mode="lines", name="LIVE Output I(t)",
                             line=dict(color=out_i_col, width=3, dash="dot")), row=2, col=2)

    grid = dict(gridcolor="rgba(0, 242, 254, 0.15)", zerolinecolor="rgba(0, 242, 254, 0.3)")
    fig.update_xaxes(**grid, title_text="time (s)", row=2)
    fig.update_xaxes(**grid)
    fig.update_yaxes(**grid)
    fig.update_yaxes(title_text="V", row=1, col=1)
    fig.update_yaxes(title_text="V", row=1, col=2)
    fig.update_yaxes(title_text="A", row=2, col=1)
    fig.update_yaxes(title_text="A", row=2, col=2)
    fig.add_annotation(
        xref="paper", yref="paper", x=0.5, y=-0.20, showarrow=False,
        text=f"Telemetry representation: sine model from measured amplitude and frequency "
             f"({f_draw:.1f} Hz{'' if freq_val and freq_val > 0 else ' assumed - no frequency reported'}). "
             f"Not raw ESP32 samples.",
        font=dict(size=10, color="#8fa3b8"))
    fig.update_layout(
        height=520, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(3, 7, 18, 0.65)",
        font=dict(color="#00f2fe", family="Orbitron", size=11),
        margin=dict(l=20, r=20, t=45, b=70), hovermode="x unified", showlegend=False)
    return fig


def _tele_card(title, value_txt, source, color):
    dot = "● HELD" if source == "HELD" else "● LIVE"
    return (
        f'<div class="os-card" style="border-left:5px solid {color} !important; text-align:center; padding:14px !important; margin-bottom:10px !important;">'
        f'<div style="font-family:Orbitron,sans-serif; font-size:0.72rem; letter-spacing:1px; color:{color};">{title}</div>'
        f'<div style="color:#c8d6e5; font-size:0.8rem; margin-top:4px;">{source} VALUE:</div>'
        f'<div style="font-family:Orbitron,sans-serif; font-size:1.55rem; color:#ffffff;">{value_txt}</div>'
        f'<div style="color:{color}; font-weight:700; font-size:0.8rem;">{dot}</div></div>')


def render_nexus_telemetry(sensor_data):
    held = sensor_data.get("source") == "HELD"
    in_src = "HELD" if held else "LIVE"
    in_col = "#ffb703" if held else "#00f2fe"
    out_col = "#00ff87"

    in_v, in_i = sensor_data["input_v"], sensor_data["input_i"]
    out_v, out_i = sensor_data["output_v"], sensor_data["output_i"]
    freq = sensor_data["frequency"]

    p_in, p_out, _ = compute_power_efficiency(in_v, in_i, out_v, out_i)

    st.markdown("### 📈 NEXUS TELEMETRY")
    st.markdown(
        f'<div style="text-align:center; font-family:Orbitron,sans-serif; letter-spacing:1px; color:#c8d6e5; margin-bottom:8px;">'
        f'<span style="color:{in_col};">{in_src} INPUT</span> &nbsp;VS&nbsp; <span style="color:{out_col};">LIVE OUTPUT</span></div>',
        unsafe_allow_html=True)

    c_in, c_out = st.columns(2)
    with c_in:
        st.markdown(f'<div style="font-family:Orbitron,sans-serif; color:{in_col}; font-weight:700; text-align:center;">INPUT TELEMETRY</div>', unsafe_allow_html=True)
        st.markdown(_tele_card(f"{in_src} INPUT VOLTAGE", f"{in_v:.2f} V", in_src, in_col), unsafe_allow_html=True)
        st.markdown(_tele_card(f"{in_src} INPUT CURRENT", f"{in_i:.3f} A", in_src, in_col), unsafe_allow_html=True)
    with c_out:
        st.markdown(f'<div style="font-family:Orbitron,sans-serif; color:{out_col}; font-weight:700; text-align:center;">OUTPUT TELEMETRY</div>', unsafe_allow_html=True)
        st.markdown(_tele_card("LIVE OUTPUT VOLTAGE", f"{out_v:.2f} V", "LIVE", out_col), unsafe_allow_html=True)
        st.markdown(_tele_card("LIVE OUTPUT CURRENT", f"{out_i:.3f} A", "LIVE", out_col), unsafe_allow_html=True)

    row = lambda k, v, c="#c8d6e5": (f'<div style="display:flex; justify-content:space-between;"><span style="color:{c};">{k}</span>'
                                     f'<span style="color:#ffffff; font-family:Orbitron,sans-serif;">{v}</span></div>')
    st.markdown(
        '<div class="os-card" style="padding:16px !important;">'
        f'<div style="font-family:Orbitron,sans-serif; color:#9d4edd; letter-spacing:1px; margin-bottom:6px;">POWER - {in_src} INPUT P vs LIVE OUTPUT P</div>'
        + row(f"{in_src} INPUT VOLTAGE", f"{in_v:.2f} V", in_col)
        + row(f"{in_src} INPUT CURRENT", f"{in_i:.3f} A", in_col)
        + row("LIVE OUTPUT VOLTAGE", f"{out_v:.2f} V", out_col)
        + row("LIVE OUTPUT CURRENT", f"{out_i:.3f} A", out_col)
        + '<hr style="border-color:rgba(0,242,254,0.2); margin:6px 0;">'
        + row("INPUT POWER (V x I)", f"{p_in:.2f} W", in_col)
        + row("OUTPUT POWER (V x I)", f"{p_out:.2f} W", out_col)
        + '</div>', unsafe_allow_html=True)

    st.plotly_chart(generate_waveform_chart(freq, in_v, out_v, in_i, out_i, input_held=held),
                    use_container_width=True)

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

@st.cache_resource
def get_cached_gemini_client(api_key):
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        print(f"Gemini Client Init Error: {e}", flush=True)
        return None

def get_gemini_client():
    api_key = st.session_state.get("api_key") or os.environ.get("GEMINI_API_KEY")
    return get_cached_gemini_client(api_key)

def get_mqtt_status_display_text():
    status = get_mqtt_status()
    if status == "Connected":
        return "Connected"
    elif status == "Waiting for Data":
        return "Connected — Waiting for Data"
    return "Disconnected"

GEMINI_MODEL_NAME = 'gemini-3.6-flash'

def _fmt(value, nd=2):
    try:
        return f"{float(value):.{nd}f}"
    except (TypeError, ValueError):
        return "N/A"

def _build_measured_block(circuit_name, source, status, targets, snap, deviations):
    in_tag = "HELD" if str(source).upper() == "HELD" else "LIVE"
    return f"""NEXUS AI DIAGNOSTIC REPORT

CIRCUIT:
{circuit_name}

ANALYSIS SOURCE:
{source}

OVERALL RESULT:
{status}

MEASURED PARAMETERS:

Input Voltage ({in_tag}):
Measured: {_fmt(snap.get('input_v'))} V
Target: {_fmt(targets['target_input_voltage'])} V
Deviation: {_fmt(deviations['Input Voltage'])} %

Output Voltage (LIVE):
Measured: {_fmt(snap.get('output_v'))} V
Target: {_fmt(targets['target_output_voltage'])} V
Deviation: {_fmt(deviations['Output Voltage'])} %

Input Current ({in_tag}):
Measured: {_fmt(snap.get('input_i'), 3)} A
Target: {_fmt(targets['target_input_current'], 3)} A
Deviation: {_fmt(deviations['Input Current'])} %

Output Current (LIVE):
Measured: {_fmt(snap.get('output_i'), 3)} A
Target: {_fmt(targets['target_output_current'], 3)} A
Deviation: {_fmt(deviations['Output Current'])} %

Input Power:
{_fmt(snap.get('power_in'))} W

Output Power:
{_fmt(snap.get('power_out'))} W

Efficiency:
{_fmt(snap.get('efficiency'))} %
"""

def _extract_percent(text, label):
    m = re.search(rf"{label}\s*:?\s*\**\s*\n?\s*\**\s*(\d{{1,3}}(?:\.\d+)?)\s*%", text or "", re.IGNORECASE)
    if not m:
        return None
    try:
        return max(0, min(100, int(round(float(m.group(1))))))
    except ValueError:
        return None

_VALID_CONDITIONS = ("NORMAL", "WARNING", "FAULT", "CRITICAL")

def build_diagnostic_payload(snap, source, frequency, temperature):
    in_src = "HELD" if str(source).upper() == "HELD" else "LIVE"
    k = in_src.lower()
    return {
        "data_sources": {
            "input_voltage": in_src, "input_current": in_src,
            "output_voltage": "LIVE", "output_current": "LIVE",
            "frequency": "LIVE", "temperature": "LIVE",
        },
        "values": {
            f"{k}_input_voltage": round(float(snap.get("input_v", 0)), 3),
            f"{k}_input_current": round(float(snap.get("input_i", 0)), 4),
            "live_output_voltage": round(float(snap.get("output_v", 0)), 3),
            "live_output_current": round(float(snap.get("output_i", 0)), 4),
            "live_frequency": round(float(frequency or 0), 2),
            "live_temperature": round(float(temperature or 0), 2),
            "input_power_w": snap.get("power_in"),
            "output_power_w": snap.get("power_out"),
            "efficiency_percent": snap.get("efficiency"),
            "voltage_drop_v": snap.get("v_drop"),
        },
    }

def _normalize_condition(cond, status):
    c = str(cond or "").strip().upper()
    if c not in _VALID_CONDITIONS:
        c = {"PASS": "NORMAL", "WARNING": "WARNING"}.get(status, "FAULT")
    if status == "PASS" and c in ("FAULT", "CRITICAL"):
        c = "WARNING"
    if status == "FAIL" and c == "NORMAL":
        c = "FAULT"
    return c

def parse_gemini_json(text, status):
    if not text:
        return None
    t = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text.strip())
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b <= a:
        return None
    try:
        d = json.loads(t[a:b + 1])
    except (ValueError, TypeError):
        return None
    if not isinstance(d, dict):
        return None

    def pct(key):
        try:
            return max(0, min(100, int(round(float(d.get(key))))))
        except (TypeError, ValueError):
            return None

    steps = d.get("recommended_steps")
    if isinstance(steps, str):
        steps = [steps]
    if not isinstance(steps, list):
        steps = []
    steps = [re.sub(r"^\s*(step\s*)?\d+\s*[.):\-]\s*", "", str(x), flags=re.IGNORECASE).strip()
             for x in steps if str(x).strip()]

    guide, diag_p = pct("overall_circuit_guide_probability"), pct("overall_circuit_diagnosis_probability")
    if guide is None or diag_p is None or not steps:
        return None
    cond = _normalize_condition(d.get("circuit_condition"), status)
    problem = str(d.get("detected_problem") or "").strip()
    if not problem:
        problem = "No problem detected" if cond == "NORMAL" else "Not specified by the analysis"
    fault_p = pct("fault_probability")
    return {
        "circuit_condition": cond,
        "overall_circuit_guide_probability": guide,
        "overall_circuit_diagnosis_probability": diag_p,
        "fault_probability": fault_p if fault_p is not None else (5 if cond == "NORMAL" else None),
        "diagnosis": str(d.get("diagnosis") or "").strip(),
        "detected_problem": problem,
        "suspected_component": str(d.get("suspected_component") or "None").strip(),
        "recommended_steps": steps,
        "problem_resolution_percent": 0,
        "resolution_status": "Verification required",
        "reasoning": str(d.get("reasoning") or "").strip(),
    }

def structured_to_text(measured_block, s, frequency, temperature):
    fp = f"{s['fault_probability']} %" if s.get("fault_probability") is not None else "N/A"
    steps = "\n".join(f"{i}. {x}" for i, x in enumerate(s["recommended_steps"], 1))
    return f"""{measured_block}
LIVE FREQUENCY / TEMPERATURE:
{_fmt(frequency, 1)} Hz / {_fmt(temperature, 1)} C

CIRCUIT CONDITION:
{s['circuit_condition']}

TECHNICAL ANALYSIS:
{s['diagnosis']}

DETECTED PROBLEM:
{s['detected_problem']}

SUSPECTED COMPONENT / SECTION:
{s['suspected_component']}

OVERALL CIRCUIT GUIDE:
{s['overall_circuit_guide_probability']} %

OVERALL CIRCUIT DIAGNOSIS:
{s['overall_circuit_diagnosis_probability']} %

FAULT PROBABILITY:
{fp}

DIAGNOSIS CONFIDENCE:
{s['overall_circuit_diagnosis_probability']} %

WHY:
{s['reasoning']}

RECOMMENDED TROUBLESHOOTING:
{steps}

PROBLEM RESOLUTION:
{s['problem_resolution_percent']} %
{s['resolution_status']}
"""

def build_offline_structured(circuit_info, snap, status, deviations):
    worst = max(deviations, key=deviations.get)
    max_dev = deviations[worst]
    comps = circuit_info.get("components", "N/A")
    if status == "PASS":
        cond, fault_p, conf = "NORMAL", int(round(min(10, max_dev * 1.5))), 80
        problem, suspect = "No problem detected", "None"
    elif status == "WARNING":
        cond, fault_p, conf = "WARNING", int(round(30 + (max_dev - 5.0) / 5.0 * 25)), 60
        problem = f"{worst} deviates {max_dev:.1f} % from its target (HELD input vs LIVE output comparison)."
        suspect = f"Circuit section associated with {worst.lower()}; components: {comps}"
    else:
        cond = "CRITICAL" if max_dev > 30 else "FAULT"
        fault_p, conf = int(round(min(95, 65 + (max_dev - 10.0) * 1.2))), 65
        problem = f"{worst} deviates {max_dev:.1f} % from its target (HELD input vs LIVE output comparison)."
        suspect = f"Circuit section associated with {worst.lower()}; components: {comps}"
    steps = ["Re-check the supply/input connection and the probe points listed for this circuit."]
    if status != "PASS":
        steps += [f"Re-measure {worst} with an independent instrument to confirm the reading.",
                  f"Inspect the components in the affected section for heat, discolouration or loose joints: {comps}",
                  "Check grounding and the load connection, then press VERIFY / RE-TEST."]
    else:
        steps.append("No repair is needed; repeat the test if conditions change.")
    return {
        "circuit_condition": cond,
        "overall_circuit_guide_probability": conf,
        "overall_circuit_diagnosis_probability": conf,
        "fault_probability": fault_p,
        "diagnosis": (f"[OFFLINE RULES ENGINE - no Gemini key] Largest deviation: {worst} at {max_dev:.2f} %. "
                      f"Input power {_fmt(snap.get('power_in'))} W, output power {_fmt(snap.get('power_out'))} W, "
                      f"efficiency {_fmt(snap.get('efficiency'))} % (database nominal {circuit_info.get('exp_eff', 'N/A')} %), "
                      f"voltage drop {_fmt(snap.get('v_drop'))} V."),
        "detected_problem": problem,
        "suspected_component": suspect,
        "recommended_steps": steps,
        "problem_resolution_percent": 0,
        "resolution_status": "Verification required",
        "reasoning": "Probability scales with the worst measured deviation (PASS <= 5 %, WARNING <= 10 %, FAIL > 10 %); "
                     "the offline engine compares electrical values only, so its confidence is limited.",
    }

def generate_automatic_diagnosis(circuit_name, circuit_info, sensor_snapshot, probes,
                                 frequency, temperature, analysis_source="LIVE",
                                 active_targets=None):
    snap = dict(sensor_snapshot)
    snap["frequency"] = frequency
    snap["temperature"] = temperature
    targets = active_targets if active_targets is not None else get_active_targets(circuit_info)
    status, deviations = evaluate_pass_fail_status(targets, snap)
    source = str(analysis_source).upper()
    payload = build_diagnostic_payload(snap, source, frequency, temperature)

    base = {"ok": False, "text": "", "error": None, "engine": "GEMINI", "status": status,
            "deviations": deviations, "targets": targets,
            "fault_probability": None, "confidence": None,
            "structured": None, "payload": payload}

    measured_block = _build_measured_block(circuit_name, source, status, targets, snap, deviations)

    client = get_gemini_client()
    if client is None:
        s = build_offline_structured(circuit_info, snap, status, deviations)
        base.update(ok=True, engine="OFFLINE RULES ENGINE", structured=s,
                    text=structured_to_text(measured_block, s, frequency, temperature),
                    fault_probability=s["fault_probability"],
                    confidence=s["overall_circuit_diagnosis_probability"])
        return base

    t_in_p = targets["target_input_voltage"] * targets["target_input_current"]
    t_out_p = targets["target_output_voltage"] * targets["target_output_current"]
    t_eff = (t_out_p / t_in_p * 100.0) if t_in_p > 0 else 0.0
    in_src = "HELD" if source == "HELD" else "LIVE"

    prompt = f"""You are the diagnostic engine of NEXUS, an AI-based electronic circuit tester. This is a CIRCUIT DIAGNOSTIC COMPARISON: decide whether the circuit behaves correctly by comparing the {in_src} INPUT condition (voltage and current) against the LIVE OUTPUT condition (voltage and current).

DATA SOURCES (authoritative JSON - the numbers below are the ONLY data to analyse):
{json.dumps(payload, indent=2)}

{'Input voltage and input current are HELD values captured at ' + str(snap.get('captured_at') or 'N/A') + ' and no longer change. Output voltage, output current, frequency and temperature are LIVE readings taken now. Do not treat the held input as a live reading.' if source == 'HELD' else 'All values are LIVE readings taken now.'}

CIRCUIT DATABASE (authoritative - do NOT invent components that are not listed here):
Circuit = {circuit_name}
Description = {circuit_info.get('description', 'N/A')}
Components = {circuit_info.get('components', 'N/A')}
Topology = {circuit_info.get('diagram', 'N/A')}
Probe Locations = {probes}
Database nominal efficiency = {circuit_info.get('exp_eff', 'N/A')} %

EXPECTED (USER CONFIGURED / DATABASE) VALUES:
Target Input Voltage = {targets['target_input_voltage']} V
Target Output Voltage = {targets['target_output_voltage']} V
Target Input Current = {targets['target_input_current']} A
Target Output Current = {targets['target_output_current']} A
Target Input Power = {t_in_p:.2f} W
Target Output Power = {t_out_p:.2f} W
Target Efficiency (from targets) = {t_eff:.2f} %

DERIVED VALUES:
Input Power = {_fmt(snap.get('power_in'))} W ({in_src} V x {in_src} I)
Output Power = {_fmt(snap.get('power_out'))} W (LIVE V x LIVE I)
Efficiency = {_fmt(snap.get('efficiency'))} %
Voltage Drop (Vin - Vout) = {_fmt(snap.get('v_drop'))} V
Frequency = {_fmt(frequency, 1)} Hz  (0 may mean the sensor does not report it)
Temperature = {_fmt(temperature, 1)} C  (0 may mean the sensor does not report it)

PYTHON-COMPUTED DEVIATIONS (|Measured - Target| / Target x 100):
Input Voltage = {deviations['Input Voltage']:.2f} %
Output Voltage = {deviations['Output Voltage']:.2f} %
Input Current = {deviations['Input Current']:.2f} %
Output Current = {deviations['Output Current']:.2f} %
PYTHON-COMPUTED OVERALL RESULT = {status}  (PASS: all within +-5 %; WARNING: any >5 % and <=10 %; FAIL: any >10 %). circuit_condition must be consistent with it: PASS -> NORMAL (or WARNING only if temperature/frequency justify it), WARNING -> WARNING, FAIL -> FAULT or CRITICAL.

ANALYSIS REQUIREMENTS:
- Consider input voltage, input current, output voltage, output current, input power, output power, efficiency, voltage drop, current relationship, frequency, temperature and the expected values above.
- Relate the pattern to THIS circuit's topology, components and probe locations.
- If the measurements indicate normal operation, say so: circuit_condition NORMAL, detected_problem "No problem detected", and do NOT invent a fault.
- Use probabilistic language; never claim a component is definitely faulty unless the numbers prove it.
- overall_circuit_guide_probability (0-100): your confidence that the recommended_steps are the right guidance for this situation.
- overall_circuit_diagnosis_probability (0-100): your confidence that the diagnosis / detected_problem is correct. Only electrical values are available, so be conservative.
- fault_probability (0-100): estimated chance that a real fault exists.
- recommended_steps: ordered, specific to this circuit and the measured values, ending with a re-test step.
- problem_resolution_percent must be 0 and resolution_status must be "Verification required": nothing has been repaired or re-measured yet.
- Plain text inside the JSON strings (no markdown).

Respond with ONLY one JSON object, no code fences, with exactly these keys:
""" + """{
  "circuit_condition": "NORMAL | WARNING | FAULT | CRITICAL",
  "overall_circuit_guide_probability": 0,
  "overall_circuit_diagnosis_probability": 0,
  "fault_probability": 0,
  "diagnosis": "technical analysis referring to the measured numbers",
  "detected_problem": "suspected problem, or No problem detected",
  "suspected_component": "component/section from the database, or None",
  "recommended_steps": ["Step 1", "Step 2", "Step 3", "Re-test the circuit"],
  "problem_resolution_percent": 0,
  "resolution_status": "Verification required",
  "reasoning": "why these probabilities and this condition were assigned, citing the numbers"
}"""

    try:
        from google.genai import types
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME, contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2))
        raw_text = (response.text or "").strip()
    except Exception as e:
        base["error"] = f"Gemini API error: {e}"
        return base

    if not raw_text:
        base["error"] = "Gemini returned an empty response."
        return base

    s = parse_gemini_json(raw_text, status)
    if s is None:
        base.update(ok=True, text=raw_text.replace("**", "").strip(),
                    fault_probability=_extract_percent(raw_text, "FAULT PROBABILITY"),
                    confidence=_extract_percent(raw_text, "DIAGNOSIS CONFIDENCE"))
        return base

    base.update(ok=True, structured=s,
                text=structured_to_text(measured_block, s, frequency, temperature),
                fault_probability=s["fault_probability"],
                confidence=s["overall_circuit_diagnosis_probability"])
    return base

def save_gemini_to_history(circuit_name, user_question, answer, metrics=None, status=None):
    if not user_question or not str(user_question).strip():
        return
    if not answer or not str(answer).strip():
        return
    metrics = metrics or {}
    now = datetime.datetime.now()
    st.session_state.historical_tests.append({
        "Date": now.strftime("%Y-%m-%d"),
        "Time": now.strftime("%H:%M:%S"),
        "Circuit": circuit_name,
        "Status": status if status else "N/A",
        "Input Voltage (V)": f"{metrics.get('input_v')} V" if metrics.get('input_v') is not None else "N/A",
        "Output Voltage (V)": f"{metrics.get('output_v')} V" if metrics.get('output_v') is not None else "N/A",
        "Efficiency %": f"{metrics.get('efficiency')} %" if metrics.get('efficiency') is not None else "N/A",
        "AI Answer / Diagnosis": str(answer),
        "User Question": str(user_question)
    })

_PDF_CHAR_MAP = {
    "Ω": " ohm", "Ω": " ohm", "µ": "u", "μ": "u", "—": "-", "–": "-", "→": "->",
    "≤": "<=", "≥": ">=", "±": "+/-", "×": "x", "✓": "", "⚡": "",
}

def _pdf_safe(value):
    text = str(value if value is not None else "N/A")
    for k, v in _PDF_CHAR_MAP.items():
        text = text.replace(k, v)
    text = text.encode("latin-1", "replace").decode("latin-1")
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

_DIAG_HEADINGS = {
    "NEXUS AI DIAGNOSTIC REPORT", "CIRCUIT", "ANALYSIS SOURCE", "OVERALL RESULT", "MEASURED PARAMETERS",
    "TECHNICAL ANALYSIS", "PROBABLE FAULT", "SUSPECTED COMPONENT / SECTION", "FAULT PROBABILITY",
    "DIAGNOSIS CONFIDENCE", "WHY", "RECOMMENDED TROUBLESHOOTING", "FINAL CONCLUSION",
    "CIRCUIT CONDITION", "DETECTED PROBLEM", "OVERALL CIRCUIT GUIDE", "OVERALL CIRCUIT DIAGNOSIS",
    "PROBLEM RESOLUTION", "LIVE FREQUENCY / TEMPERATURE",
}

def generate_diagnostic_report_pdf(result):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
                            leftMargin=16 * mm, rightMargin=16 * mm,
                            title="NEXUS AI Electronic Circuit Diagnostic Report")
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    small = ParagraphStyle("nx_small", parent=normal, fontSize=9, leading=12)
    h2 = ParagraphStyle("nx_h2", parent=styles["Heading2"], textColor=colors.HexColor("#0b3c5d"), spaceBefore=10, spaceAfter=4)
    sub = ParagraphStyle("nx_sub", parent=normal, alignment=1, fontSize=11, textColor=colors.HexColor("#0b3c5d"))
    title = ParagraphStyle("nx_title", parent=styles["Title"], fontSize=16, leading=20, textColor=colors.HexColor("#0b3c5d"))
    diag_head = ParagraphStyle("nx_dh", parent=normal, fontName="Helvetica-Bold", fontSize=10, spaceBefore=6, textColor=colors.HexColor("#0b3c5d"))
    diag_body = ParagraphStyle("nx_db", parent=normal, fontSize=9.5, leading=13)

    def tbl(rows, widths, header=True, align_right_from=None):
        t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
        style = [
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9fb3c8")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        if header:
            style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b3c5d")),
                      ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                      ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
        if align_right_from is not None:
            style.append(("ALIGN", (align_right_from, 0), (-1, -1), "RIGHT"))
        t.setStyle(TableStyle(style))
        return t

    ts = result["timestamp"]
    info = result["circuit_info"]
    snap = result["sensor"]
    targets = result["targets"]
    dev = result["deviations"]
    el = []

    el.append(Paragraph("NEXUS - AI-BASED ELECTRONIC CIRCUIT TESTER", title))
    el.append(Paragraph("<b>AI ELECTRONIC CIRCUIT DIAGNOSTIC REPORT</b>", sub))
    el.append(Spacer(1, 8))

    el.append(Paragraph("Project Information", h2))
    rows = [
        ["Selected circuit", _pdf_safe(result["circuit"])],
        ["Circuit category", _pdf_safe(result.get("category", "N/A"))],
        ["Date", ts.strftime("%Y-%m-%d")],
        ["Time", ts.strftime("%H:%M:%S")],
        ["Analysis source", _pdf_safe(result["source"])],
        ["ESP32 status", _pdf_safe(result.get("esp32_status", "N/A"))],
        ["MQTT status", _pdf_safe(result.get("mqtt_status", "N/A"))],
        ["Analysis engine", _pdf_safe(result.get("engine", "GEMINI"))],
    ]
    if result["source"] == "HELD" and snap.get("captured_at"):
        rows.insert(5, ["Snapshot captured", snap["captured_at"].strftime("%H:%M:%S")])
    rows = [[Paragraph(f"<b>{a}</b>", small), Paragraph(b, small)] for a, b in rows]
    el.append(tbl(rows, [45 * mm, 130 * mm], header=False))

    el.append(Paragraph("Circuit Information", h2))
    el.append(Paragraph(f"<b>Description:</b> {_pdf_safe(info.get('description'))}", small))
    el.append(Paragraph(f"<b>Components:</b> {_pdf_safe(info.get('components'))}", small))
    el.append(Paragraph(f"<b>Circuit topology:</b> {_pdf_safe(info.get('diagram'))}", small))
    el.append(Paragraph("<b>Probe locations:</b>", small))
    for pr in info.get("probes", []):
        el.append(Paragraph(f"&nbsp;&nbsp;Step {_pdf_safe(pr.get('step'))} - {_pdf_safe(pr.get('name'))}: {_pdf_safe(pr.get('loc'))}", small))

    el.append(Paragraph("Target vs Measured", h2))
    data = [["Parameter", "Target", "Measured", "Deviation"],
            ["Input Voltage", f"{_fmt(targets['target_input_voltage'])} V", f"{_fmt(snap['input_v'])} V", f"{_fmt(dev['Input Voltage'])} %"],
            ["Output Voltage", f"{_fmt(targets['target_output_voltage'])} V", f"{_fmt(snap['output_v'])} V", f"{_fmt(dev['Output Voltage'])} %"],
            ["Input Current", f"{_fmt(targets['target_input_current'])} A", f"{_fmt(snap['input_i'])} A", f"{_fmt(dev['Input Current'])} %"],
            ["Output Current", f"{_fmt(targets['target_output_current'])} A", f"{_fmt(snap['output_i'])} A", f"{_fmt(dev['Output Current'])} %"]]
    el.append(tbl(data, [55 * mm, 40 * mm, 40 * mm, 40 * mm], align_right_from=1))

    el.append(Paragraph("Electrical Calculations", h2))
    calc = [["Quantity", "Value"],
            ["Input Power", f"{_fmt(snap['power_in'])} W"],
            ["Output Power", f"{_fmt(snap['power_out'])} W"],
            ["Efficiency", f"{_fmt(snap['efficiency'])} %"],
            ["Voltage Drop", f"{_fmt(snap['v_drop'])} V"],
            ["Frequency", f"{_fmt(snap['frequency'], 1)} Hz"],
            ["Temperature", f"{_fmt(snap['temperature'], 1)} C"],
            ["Circuit Health", f"{snap.get('health', 0)} %"]]
    el.append(tbl(calc, [80 * mm, 95 * mm], align_right_from=1))

    el.append(Paragraph("AI Diagnosis", h2))
    fp, cf = result.get("fault_probability"), result.get("confidence")
    summary = [["Overall result", "Fault probability", "Diagnosis confidence"],
               [_pdf_safe(result["status"]), f"{fp} %" if fp is not None else "N/A", f"{cf} %" if cf is not None else "N/A"]]
    el.append(tbl(summary, [58 * mm, 58 * mm, 59 * mm]))
    el.append(Spacer(1, 6))

    for line in result["text"].splitlines():
        clean = line.strip()
        if not clean:
            el.append(Spacer(1, 3))
            continue
        key = clean.rstrip(":").strip().upper()
        if key in _DIAG_HEADINGS and clean.endswith(":") or clean.upper() == "NEXUS AI DIAGNOSTIC REPORT":
            el.append(Paragraph(_pdf_safe(clean), diag_head))
        else:
            el.append(Paragraph(_pdf_safe(clean), diag_body))

    doc.build(el)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

def save_analysis_to_history(result):
    snap = result["sensor"]
    ts = result["timestamp"]
    result["test_id"] = new_test_id(ts)
    st.session_state.historical_tests.append({
        "Test ID": result["test_id"],
        "Date": ts.strftime("%Y-%m-%d"),
        "Time": ts.strftime("%H:%M:%S"),
        "Circuit": result["circuit"],
        "Status": result["status"],
        "Input Voltage (V)": f"{snap['input_v']} V",
        "Output Voltage (V)": f"{snap['output_v']} V",
        "Efficiency %": f"{snap['efficiency']} %",
        "AI Answer / Diagnosis": result["text"],
        "Timestamp": ts.isoformat(timespec="seconds"),
        "Analysis Source": result["source"],
        "Input Current (A)": f"{snap['input_i']} A",
        "Output Current (A)": f"{snap['output_i']} A",
        "Fault Probability": f"{result['fault_probability']} %" if result.get("fault_probability") is not None else "N/A",
        "Diagnosis Confidence": f"{result['confidence']} %" if result.get("confidence") is not None else "N/A",
    })
    # Frozen copy of this exact test, selectable on the Generate Report page.
    st.session_state.analysis_records.append({
        "test_id": result["test_id"], "kind": "analogue", "circuit": result["circuit"],
        "category": result.get("category", "N/A"), "timestamp": ts,
        "result": copy.deepcopy({k: v for k, v in result.items() if k != "pdf_bytes"}),
    })
    st.session_state.report_selected_test = result["test_id"]

def run_gemini_analysis(circuit_info, active_targets):
    packet, packet_time = get_latest_packet_and_time()
    if packet is None:
        st.warning("No valid sensor data available for analysis.")
        return
    esp_state, age = get_esp32_status()
    if esp_state != "ONLINE":
        age_txt = f"{age:.0f} s ago" if age is not None else "unknown"
        st.warning(f"ESP32 is {esp_state} (last valid packet: {age_txt}). Analysis needs fresh live output telemetry - wait for the ESP32.")
        return
    if is_data_held():
        raw = merge_held_input(packet)
        snapshot = build_sensor_data(raw, circuit_info)
        snapshot["packet_time"] = packet_time
        snapshot["captured_at"] = st.session_state.held_input_data["captured_at"]
        source = "HELD"
    else:
        raw = packet
        snapshot = get_live_sensor_data(circuit_info)
        source = "LIVE"

    missing = validate_sensor_packet(raw)
    if missing:
        st.error("Cannot analyse - required measurement(s) missing from the packet: " + ", ".join(missing))
        return

    with st.spinner("Gemini is analysing the measurement snapshot..."):
        diag = generate_automatic_diagnosis(
            st.session_state.selected_circuit, circuit_info, snapshot,
            circuit_info["probes"], snapshot["frequency"], snapshot["temperature"],
            analysis_source=source, active_targets=active_targets,
        )

    if not diag["ok"]:
        st.error(f"⚠️ {diag['error']}  Your {'held ' if source == 'HELD' else ''}measurement is unchanged - press ANALYZE WITH GEMINI to retry.")
        return

    esp_state, esp_age = get_esp32_status()
    esp_txt = esp_state + (f" (last packet {esp_age:.1f} s ago)" if esp_age is not None else "")
    result = {
        "timestamp": datetime.datetime.now(),
        "circuit": st.session_state.selected_circuit,
        "category": st.session_state.selected_category,
        "circuit_info": {k: circuit_info.get(k) for k in ("description", "components", "diagram", "probes", "exp_eff")},
        "targets": diag["targets"],
        "sensor": snapshot,
        "deviations": diag["deviations"],
        "status": diag["status"],
        "source": source,
        "esp32_status": esp_txt,
        "mqtt_status": get_mqtt_connection_status().upper(),
        "engine": diag["engine"],
        "text": diag["text"],
        "fault_probability": diag["fault_probability"],
        "confidence": diag["confidence"],
        "pdf_bytes": None,
        "structured": diag.get("structured"),
        "payload": diag.get("payload"),
        "baseline": make_resolution_baseline(snapshot, diag["deviations"], diag["targets"]),
        "resolution": initial_resolution(diag["status"]),
        "verifications": [],
    }
    st.session_state.last_gemini_result = result
    save_analysis_to_history(result)
    speak_text(result["text"])

RESOLUTION_TOLERANCE_PCT = 5.0

def make_resolution_baseline(snapshot, deviations, targets):
    return {
        "deviations": dict(deviations),
        "efficiency": snapshot.get("efficiency"),
        "input_v": snapshot.get("input_v"), "input_i": snapshot.get("input_i"),
        "output_v": snapshot.get("output_v"), "output_i": snapshot.get("output_i"),
    }

def initial_resolution(status):
    if status == "PASS":
        return {"percent": 100, "status": "No problem detected - nothing to resolve",
                "reasoning": ["All four measurements were within +-5 % of target when analysed."],
                "terms": [], "verified_at": None, "source": None}
    return {"percent": 0, "status": "Verification required",
            "reasoning": ["Follow the recommended steps, then press VERIFY / RE-TEST to measure the result."],
            "terms": [], "verified_at": None, "source": None}

def _target_efficiency(targets):
    t_in = targets["target_input_voltage"] * targets["target_input_current"]
    t_out = targets["target_output_voltage"] * targets["target_output_current"]
    return (t_out / t_in * 100.0) if t_in > 0 else 0.0

def compute_problem_resolution(baseline, new_snap, targets, new_source):
    tol = RESOLUTION_TOLERANCE_PCT
    new_status, new_dev = evaluate_pass_fail_status(targets, new_snap)
    terms = []

    def add(name, d0, d1):
        if d0 > tol:
            if d1 <= tol:
                r, note = 1.0, "back within tolerance"
            elif d1 >= d0 - 0.05:
                r, note = 0.0, ("worse" if d1 > d0 + 0.05 else "unchanged")
            else:
                r, note = (d0 - d1) / (d0 - tol), "improved, still outside tolerance"
        elif d1 > tol:
            r, note = 0.0, "NEW deviation (was within tolerance)"
        else:
            return
        terms.append({"name": name, "before": d0, "after": d1, "score": r, "note": note})

    for name, d1 in new_dev.items():
        add(name, baseline["deviations"][name], d1)

    t_eff = _target_efficiency(targets)
    e_before, e_after = baseline.get("efficiency"), new_snap.get("efficiency")
    if t_eff > 0 and e_before is not None and e_after is not None:
        add("Efficiency", abs(e_before - t_eff) / t_eff * 100.0, abs(e_after - t_eff) / t_eff * 100.0)

    percent = int(round(sum(t["score"] for t in terms) / len(terms) * 100)) if terms else 100
    any_worse = any(t["note"] in ("worse",) or t["note"].startswith("NEW") for t in terms)

    if not terms:
        status = "Within tolerance - no problem present"
    elif percent >= 100:
        status = "Resolved - verified by measurement"
    elif any_worse and percent == 0:
        status = "Worse than before - problem not resolved"
    elif percent >= 60:
        status = "Substantially improved - re-test after further checks"
    elif percent > 0:
        status = "Partially improved - continue troubleshooting"
    else:
        status = "Not resolved - no measurable improvement"

    lines = [f"{t['name']}: deviation {t['before']:.1f} % -> {t['after']:.1f} % ({t['note']})" for t in terms]
    if not lines:
        lines = ["No quantity was outside +-5 % before or after."]
    lines.append(f"Resolution = mean of {len(terms)} term(s) = {percent} %." if terms else "Nothing to resolve.")
    if new_source == "HELD" and any(t["name"] in ("Input Voltage", "Input Current") and t["score"] < 1 for t in terms):
        lines.append("Note: Input V/I are still HELD at the earlier capture, so their deviation cannot change. "
                     "RELEASE then HOLD again to capture the input after your repair.")
    lines.append("Based on a single live sample taken when VERIFY / RE-TEST was pressed.")
    return {"percent": percent, "status": status, "reasoning": lines, "terms": terms,
            "verified_at": datetime.datetime.now(), "source": new_source,
            "after": {"output_v": new_snap.get("output_v"), "output_i": new_snap.get("output_i"),
                      "input_v": new_snap.get("input_v"), "input_i": new_snap.get("input_i"),
                      "efficiency": new_snap.get("efficiency"), "status": new_status}}

def run_verification(result):
    if st.session_state.selected_circuit != result["circuit"]:
        st.warning(f"The selected circuit changed since the analysis ({result['circuit']}). Re-run ANALYZE for the new circuit.")
        return
    packet, _t = get_latest_packet_and_time()
    esp_state, age = get_esp32_status()
    if packet is None or esp_state != "ONLINE":
        st.warning(f"ESP32 is {esp_state}. Verification needs fresh live output telemetry.")
        return
    missing = validate_sensor_packet(merge_held_input(packet))
    if missing:
        st.error("Cannot verify - measurement(s) missing from the packet: " + ", ".join(missing))
        return
    new_snap = get_testing_sensor_data(get_current_circuit_data())
    res = compute_problem_resolution(result["baseline"], new_snap, result["targets"], new_snap["source"])
    result["resolution"] = res
    result.setdefault("verifications", []).append(res)

_COND_COLORS = {"NORMAL": "#00ff87", "WARNING": "#ffb703", "FAULT": "#ff6b35", "CRITICAL": "#ff0055"}

def _bar_html(label, pct, color):
    pct = max(0, min(100, int(pct)))
    return (f'<div style="margin:8px 0;"><div style="display:flex; justify-content:space-between; font-family:Orbitron,sans-serif; font-size:0.8rem;">'
            f'<span style="color:#c8d6e5;">{label}</span><span style="color:{color}; font-weight:700;">{pct}%</span></div>'
            f'<div style="background:rgba(255,255,255,0.08); border-radius:6px; height:12px; overflow:hidden;">'
            f'<div style="width:{pct}%; height:100%; background:{color};"></div></div></div>')

def render_nexus_ai_dashboard(result):
    s = result["structured"]
    cc = _COND_COLORS.get(s["circuit_condition"], "#00f2fe")
    steps_html = "".join(
        f'<div style="margin:6px 0;"><b style="color:#00f2fe; font-family:Orbitron,sans-serif; font-size:0.78rem;">STEP {i}</b>'
        f'<div style="color:#c8d6e5;">{html.escape(x)}</div></div>'
        for i, x in enumerate(s["recommended_steps"], 1))
    st.markdown(f"""
    <div class="os-card" style="border-left: 5px solid {cc} !important;">
        <div style="text-align:center; font-family:Orbitron,sans-serif; color:#00f2fe; letter-spacing:3px; font-weight:700; font-size:1.1rem;">NEXUS AI DIAGNOSIS</div>
        {_bar_html("OVERALL CIRCUIT GUIDE", s["overall_circuit_guide_probability"], "#00f2fe")}
        {_bar_html("OVERALL CIRCUIT DIAGNOSIS", s["overall_circuit_diagnosis_probability"], "#9d4edd")}
        <div style="margin:14px 0 6px 0; font-family:Orbitron,sans-serif;">CIRCUIT CONDITION:
            <span style="color:{cc}; font-weight:700; border:1px solid {cc}; border-radius:6px; padding:2px 10px;">{s["circuit_condition"]}</span></div>
        <div style="margin-top:10px;"><b style="color:#00f2fe; font-family:Orbitron,sans-serif; font-size:0.8rem;">DETECTED PROBLEM</b>
            <div style="color:#ffffff;">{html.escape(s["detected_problem"])}</div></div>
        <div style="margin-top:10px;"><b style="color:#00f2fe; font-family:Orbitron,sans-serif; font-size:0.8rem;">DIAGNOSIS</b>
            <div style="color:#c8d6e5;">{html.escape(s["diagnosis"])}</div></div>
        <div style="margin-top:10px;"><b style="color:#00f2fe; font-family:Orbitron,sans-serif; font-size:0.8rem;">RECOMMENDED STEPS</b>{steps_html}</div>
        <div style="margin-top:10px;"><b style="color:#00f2fe; font-family:Orbitron,sans-serif; font-size:0.8rem;">REASONING</b>
            <div style="color:#c8d6e5;">{html.escape(s["reasoning"])}</div></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("#### 🔧 CIRCUIT PROBLEM RESOLUTION")
    if result.get("baseline") is not None and result["status"] != "PASS":
        if st.button("🔁 VERIFY / RE-TEST", key="verify_retest_btn", use_container_width=True,
                     help="Follow the recommended steps first. Compares a NEW measurement (held input + live output) with the values measured at diagnosis."):
            run_verification(result)
    res = result["resolution"]
    rc = "#00ff87" if res["percent"] >= 85 else ("#ffb703" if res["percent"] >= 40 else "#ff0055")
    verified = res.get("verified_at") is not None
    if not verified and result["status"] != "PASS":
        rc = "#8fa3b8"
    n_ver = len(result.get("verifications", []))
    lines_html = "".join(f"<li>{html.escape(x)}</li>" for x in res["reasoning"])
    when = f" | VERIFIED {res['verified_at'].strftime('%H:%M:%S')} ({res['source']} input / LIVE output) | RE-TESTS: {n_ver}" if verified else ""
    st.markdown(f"""
    <div class="os-card" style="border-left: 5px solid {rc} !important;">
        {_bar_html("PROBLEM RESOLUTION", res["percent"], rc)}
        <div style="font-family:Orbitron,sans-serif; color:{rc}; font-weight:700;">{html.escape(res["status"])}<span style="color:#8fa3b8; font-weight:400; font-size:0.75rem;">{when}</span></div>
        <ul style="color:#c8d6e5; margin-top:8px;">{lines_html}</ul>
    </div>""", unsafe_allow_html=True)

def render_analysis_result(result):
    src_color = "#ffb703" if result["source"] == "HELD" else "#00ff87"
    src_note = "HELD INPUT V/I vs LIVE OUTPUT V/I (+ LIVE frequency/temperature)" if result["source"] == "HELD" else "ALL LIVE"
    st.markdown(f"""
    <div class="os-card" style="border-left: 5px solid {src_color} !important;">
        <p style="margin:0;"><b>ANALYSIS SOURCE:</b> <span style="color:{src_color};">{result['source']}</span> ({src_note})
        &nbsp;|&nbsp; <b>ENGINE:</b> {html.escape(result['engine'])}
        &nbsp;|&nbsp; <b>COMPLETED:</b> {result['timestamp'].strftime('%H:%M:%S')}</p>
    </div>
    """, unsafe_allow_html=True)

    if result.get("structured") is not None:
        render_nexus_ai_dashboard(result)
        with st.expander("📋 FULL TEXT REPORT (as saved to history / PDF)"):
            st.markdown(
                f"<pre style='white-space: pre-wrap; font-family: Rajdhani, sans-serif; font-size: 1.0rem; color: #c8d6e5;'>{html.escape(result['text'])}</pre>",
                unsafe_allow_html=True)
        if result.get("payload"):
            with st.expander("📡 DATA SENT TO GEMINI (source map + values)"):
                st.json(result["payload"])
    else:
        st.warning("Gemini did not return structured JSON - showing the raw text. Press ANALYZE WITH GEMINI to retry.")
        st.markdown(
            f"<div class='os-card'><pre style='white-space: pre-wrap; font-family: Rajdhani, sans-serif; font-size: 1.05rem; color: #c8d6e5;'>{html.escape(result['text'])}</pre></div>",
            unsafe_allow_html=True)

    if result.get("pdf_bytes") is None:
        try:
            result["pdf_bytes"] = generate_diagnostic_report_pdf(result)
        except Exception as e:
            st.error(f"PDF generation failed: {e}")
            return
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", result["circuit"])
    st.download_button(
        label="📄 DOWNLOAD DIAGNOSTIC REPORT",
        data=result["pdf_bytes"],
        file_name=f"NEXUS_Diagnostic_{safe_name}_{result['timestamp'].strftime('%Y%m%d_%H%M%S')}.pdf",
        mime="application/pdf",
        key="download_diagnostic_report_btn",
        use_container_width=True,
    )
    if st.button("📑 CREATE STUDENT TEST REPORT FROM THIS TEST →", key="goto_report_btn", use_container_width=True):
        st.session_state.report_selected_test = result.get("test_id")
        st.session_state.page = "Generate Report"
        st.rerun()

# ==============================================================================
# LOGIC / CIRCUIT DIAGRAM ENGINE (pure Python - no extra dependencies)
# One circuit definition (build_logic_diagram) is rendered twice:
#   * render_diagram_svg()      -> dashboard (inline SVG)
#   * render_diagram_drawing()  -> ReportLab vector Drawing for the PDF report
# ==============================================================================
_DIAG_STROKE = "#1b2a41"
_DIAG_FILL = "#eaf4ff"
_DIAG_WIRE = "#1b2a41"
_DIAG_CAPTION = "#5b6b80"


class LogicDiagram:
    """Tiny scene description: wires, standard gate symbols, dots and text.
    Coordinates are SVG-style (origin top-left, y grows downwards)."""

    GATE_W = 50.0
    GATE_H = 40.0

    def __init__(self, width, height, title="Logic diagram"):
        self.width = float(width)
        self.height = float(height)
        self.title = title
        self.items = []

    # -- primitives ---------------------------------------------------------
    def wire(self, *pts):
        self.items.append(("poly", [(float(x), float(y)) for x, y in pts]))

    def dot(self, x, y):
        self.items.append(("circle", float(x), float(y), 3.2, True))

    def text(self, x, y, s, anchor="middle", size=12, bold=False, color=_DIAG_STROKE):
        self.items.append(("text", float(x), float(y), str(s), anchor, float(size), bool(bold), color))

    def box(self, x, y, w, h, label=None):
        self.items.append(("rect", float(x), float(y), float(w), float(h)))
        if label:
            self.text(x + w / 2.0, y + h / 2.0 + 4, label, size=12, bold=True)

    # -- standard gate symbols ---------------------------------------------
    def gate(self, kind, x, y, caption=None):
        """Draws a standard gate symbol with its top-left body corner at (x, y).
        Returns the pin coordinates: {'a': (x, y), 'b': (x, y), 'out': (x, y)}
        (NOT gates only have 'a')."""
        kind = kind.upper()
        W, H = self.GATE_W, self.GATE_H
        inverted = kind in ("NAND", "NOR", "XNOR", "NOT")
        pins = {}
        if kind == "NOT":
            tri = [("M", x, y + 4), ("L", x, y + H - 4), ("L", x + 36, y + H / 2), ("Z",)]
            self.items.append(("path", tri, True))
            self.items.append(("circle", x + 40, y + H / 2, 4.0, False))
            pins["a"] = (x, y + H / 2)
            pins["out"] = (x + 44, y + H / 2)
            if caption:
                self.text(x + 22, y + H + 12, caption, size=9, color=_DIAG_CAPTION)
            return pins

        base = kind[1:] if kind in ("NAND", "NOR", "XNOR") else kind
        if base == "AND":
            cx, cy = x + 25.0, y + H / 2.0
            cmds = [("M", x, y), ("L", cx, y)]
            steps = 14
            for i in range(1, steps + 1):
                a = math.radians(-90.0 + 180.0 * i / steps)
                cmds.append(("L", cx + 25.0 * math.cos(a), cy + 20.0 * math.sin(a)))
            cmds += [("L", x, y + H), ("Z",)]
            pin_x = x
        else:  # OR / XOR family
            cmds = [("M", x, y), ("Q", x + 28, y, x + W, y + H / 2),
                    ("Q", x + 28, y + H, x, y + H),
                    ("Q", x + 12, y + H / 2, x, y), ("Z",)]
            pin_x = x + 4.5
        self.items.append(("path", cmds, True))
        if base == "XOR":
            self.items.append(("path", [("M", x - 6, y), ("Q", x + 6, y + H / 2, x - 6, y + H)], False))
            pin_x = x - 1.5
        pins["a"] = (pin_x, y + 10)
        pins["b"] = (pin_x, y + 30)
        if inverted:
            self.items.append(("circle", x + W + 4, y + H / 2, 4.0, False))
            pins["out"] = (x + W + 8, y + H / 2)
        else:
            pins["out"] = (x + W, y + H / 2)
        if caption:
            self.text(x + W / 2.0, y + H + 12, caption, size=9, color=_DIAG_CAPTION)
        return pins


def _bus_inputs(d, names, bus_xs, feed_ys, bus_ends, label_x=30, start_x=36):
    """Draws labelled input feeds and vertical buses. Returns a tap(name, y, to_x) helper."""
    info = {}
    for nm, bx, fy, be in zip(names, bus_xs, feed_ys, bus_ends):
        d.text(label_x, fy + 4, nm, anchor="end", size=13, bold=True)
        d.wire((start_x, fy), (bx, fy), (bx, be))
        info[nm] = (bx, fy)

    def tap(name, y, to_x, dot=True):
        bx, fy = info[name]
        if dot and abs(y - fy) > 0.1:
            d.dot(bx, y)
        d.wire((bx, y), (to_x, y))
    return tap


def _out_label(d, pin, label, length=70):
    x, y = pin
    d.wire((x, y), (x + length, y))
    d.text(x + length + 8, y + 4, label, anchor="start", size=13, bold=True)


def _build_single_gate(kind, label_out="Y"):
    d = LogicDiagram(400, 120, f"{kind} gate")
    gx, gy = 150, 40
    p = d.gate(kind, gx, gy)
    d.text(30, p["a"][1] + 4, "A", anchor="end", size=13, bold=True)
    d.text(30, p["b"][1] + 4, "B", anchor="end", size=13, bold=True)
    d.wire((36, p["a"][1]), p["a"])
    d.wire((36, p["b"][1]), p["b"])
    _out_label(d, p["out"], label_out, 80)
    return d


def _build_not():
    d = LogicDiagram(400, 120, "NOT gate")
    p = d.gate("NOT", 150, 40)
    d.text(30, p["a"][1] + 4, "A", anchor="end", size=13, bold=True)
    d.wire((36, p["a"][1]), p["a"])
    _out_label(d, p["out"], "Y", 90)
    return d


def _build_half_adder():
    d = LogicDiagram(480, 230, "Half adder")
    tap = _bus_inputs(d, ["A", "B"], [70, 90], [30, 50], [150, 170])
    x1 = d.gate("XOR", 220, 70, "XOR")
    a1 = d.gate("AND", 220, 140, "AND")
    tap("A", x1["a"][1], x1["a"][0]); tap("B", x1["b"][1], x1["b"][0])
    tap("A", a1["a"][1], a1["a"][0]); tap("B", a1["b"][1], a1["b"][0])
    _out_label(d, x1["out"], "Sum", 90)
    _out_label(d, a1["out"], "Carry", 90)
    return d


def _build_full_adder():
    d = LogicDiagram(610, 330, "Full adder")
    tap = _bus_inputs(d, ["A", "B", "Cin"], [60, 80, 100], [30, 50, 70], [260, 280, 200])
    x1 = d.gate("XOR", 180, 90, "XOR 1")
    x2 = d.gate("XOR", 320, 90, "XOR 2")
    a1 = d.gate("AND", 180, 250, "AND 1")
    a2 = d.gate("AND", 320, 170, "AND 2")
    o1 = d.gate("OR", 440, 210, "OR")
    # inputs to XOR 1 and AND 1
    tap("A", x1["a"][1], x1["a"][0]); tap("B", x1["b"][1], x1["b"][0])
    tap("A", a1["a"][1], a1["a"][0]); tap("B", a1["b"][1], a1["b"][0])
    # (A xor B) -> XOR 2 (in a) and AND 2 (in a)
    ox, oy = x1["out"]
    d.wire((ox, oy), (290, oy), (290, x2["a"][1]), (x2["a"][0], x2["a"][1]))
    d.dot(260, oy)
    d.wire((260, oy), (260, a2["a"][1]), (a2["a"][0], a2["a"][1]))
    # Cin -> XOR 2 (in b) and AND 2 (in b)
    d.dot(100, 150)
    d.wire((100, 150), (305, 150), (305, x2["b"][1]), (x2["b"][0], x2["b"][1]))
    d.dot(100, a2["b"][1])
    d.wire((100, a2["b"][1]), (a2["b"][0], a2["b"][1]))
    # outputs
    _out_label(d, x2["out"], "Sum", 120)
    ax, ay = a2["out"]
    d.wire((ax, ay), (415, ay), (415, o1["a"][1]), (o1["a"][0], o1["a"][1]))
    bx, by = a1["out"]
    d.wire((bx, by), (430, by), (430, o1["b"][1]), (o1["b"][0], o1["b"][1]))
    _out_label(d, o1["out"], "Carry-out", 40)
    return d


def _build_half_subtractor():
    d = LogicDiagram(520, 250, "Half subtractor")
    tap = _bus_inputs(d, ["A", "B"], [70, 90], [30, 50], [160, 180])
    x1 = d.gate("XOR", 230, 70, "XOR")
    n1 = d.gate("NOT", 130, 140)
    a1 = d.gate("AND", 230, 150, "AND")
    tap("A", x1["a"][1], x1["a"][0]); tap("B", x1["b"][1], x1["b"][0])
    tap("A", n1["a"][1], n1["a"][0])
    d.wire(n1["out"], (a1["a"][0], n1["out"][1]))
    tap("B", a1["b"][1], a1["b"][0])
    _out_label(d, x1["out"], "Difference", 90)
    _out_label(d, a1["out"], "Borrow", 90)
    return d


def _build_full_subtractor():
    d = LogicDiagram(640, 330, "Full subtractor")
    tap = _bus_inputs(d, ["A", "B", "Bin"], [60, 80, 100], [30, 50, 70], [270, 300, 230])
    x1 = d.gate("XOR", 180, 90, "XOR 1")
    x2 = d.gate("XOR", 320, 90, "XOR 2")
    nx = d.gate("NOT", 270, 175)
    a2 = d.gate("AND", 350, 175, "AND 2")
    na = d.gate("NOT", 130, 250)
    a1 = d.gate("AND", 220, 250, "AND 1")
    o1 = d.gate("OR", 440, 210, "OR")
    tap("A", x1["a"][1], x1["a"][0]); tap("B", x1["b"][1], x1["b"][0])
    # (A xor B) -> XOR 2 and NOT
    ox, oy = x1["out"]
    d.wire((ox, oy), (280, oy), (280, x2["a"][1]), (x2["a"][0], x2["a"][1]))
    d.dot(250, oy)
    d.wire((250, oy), (250, nx["a"][1]), nx["a"])
    # Bin -> XOR 2 (b) and AND 2 (b)
    d.dot(100, 150)
    d.wire((100, 150), (300, 150), (300, x2["b"][1]), (x2["b"][0], x2["b"][1]))
    d.dot(100, 230)
    d.wire((100, 230), (335, 230), (335, a2["b"][1]), (a2["b"][0], a2["b"][1]))
    d.wire(nx["out"], (330, nx["out"][1]), (330, a2["a"][1]), (a2["a"][0], a2["a"][1]))
    # NOT A and AND 1
    tap("A", na["a"][1], na["a"][0])
    d.wire(na["out"], (197, na["out"][1]), (197, a1["a"][1]), (a1["a"][0], a1["a"][1]))
    tap("B", 300, 205)
    d.wire((205, 300), (205, a1["b"][1]), (a1["b"][0], a1["b"][1]))
    # outputs
    _out_label(d, x2["out"], "Difference", 90)
    ax, ay = a2["out"]
    d.wire((ax, ay), (420, ay), (420, o1["a"][1]), (o1["a"][0], o1["a"][1]))
    bx, by = a1["out"]
    d.wire((bx, by), (430, by), (430, o1["b"][1]), (o1["b"][0], o1["b"][1]))
    _out_label(d, o1["out"], "Borrow-out", 40)
    return d


def _build_mux_2_1():
    d = LogicDiagram(540, 270, "2:1 multiplexer")
    tap = _bus_inputs(d, ["S", "I0", "I1"], [60, 80, 100], [30, 50, 70], [190, 130, 210])
    n1 = d.gate("NOT", 140, 80)
    a1 = d.gate("AND", 230, 100, "AND 1")
    a2 = d.gate("AND", 230, 180, "AND 2")
    o1 = d.gate("OR", 350, 130, "OR")
    tap("S", n1["a"][1], n1["a"][0])
    d.wire(n1["out"], (207, n1["out"][1]), (207, a1["a"][1]), (a1["a"][0], a1["a"][1]))
    tap("I0", a1["b"][1], a1["b"][0])
    tap("S", a2["a"][1], a2["a"][0])
    tap("I1", a2["b"][1], a2["b"][0])
    ax, ay = a1["out"]
    d.wire((ax, ay), (310, ay), (310, o1["a"][1]), (o1["a"][0], o1["a"][1]))
    bx, by = a2["out"]
    d.wire((bx, by), (325, by), (325, o1["b"][1]), (o1["b"][0], o1["b"][1]))
    _out_label(d, o1["out"], "Y", 80)
    return d


def _build_bin_to_gray(n):
    n = max(2, min(int(n), 4))
    spacing, y0 = 70, 40
    d = LogicDiagram(520, y0 + spacing * (n - 1) + 70, f"{n}-bit binary to Gray converter")
    rows = [y0 + spacing * k for k in range(n)]
    for k in range(n):
        bit = n - 1 - k
        d.text(30, rows[k] + 4, f"B{bit}", anchor="end", size=13, bold=True)
        end_x = 410 if k == 0 else 190
        d.wire((36, rows[k]), (end_x, rows[k]))
    d.text(418, rows[0] + 4, f"G{n - 1}", anchor="start", size=13, bold=True)
    for k in range(n - 1):
        g = d.gate("XOR", 240, rows[k] + 15, "XOR")
        # upper input from row k (via x=150), lower input from row k+1 (via x=190)
        d.dot(150, rows[k])
        d.wire((150, rows[k]), (150, g["a"][1]), g["a"])
        d.dot(190, rows[k + 1])
        d.wire((190, rows[k + 1]), (190, g["b"][1]), g["b"])
        _out_label(d, g["out"], f"G{n - 2 - k}", 60)
    return d


def _build_gray_to_bin(n):
    n = max(2, min(int(n), 4))
    spacing, y0 = 70, 40
    xs = [200 + 100 * (k - 1) for k in range(1, n)]
    x_end = xs[-1] + 50 + 40 + 20
    d = LogicDiagram(x_end + 60, y0 + spacing * (n - 1) + 40, f"{n}-bit Gray to binary converter")
    rows = [y0 + spacing * k for k in range(n)]
    d.text(30, rows[0] + 4, f"G{n - 1}", anchor="end", size=13, bold=True)
    d.wire((36, rows[0]), (x_end, rows[0]))
    d.text(x_end + 8, rows[0] + 4, f"B{n - 1}", anchor="start", size=13, bold=True)
    prev_out = None
    for k in range(1, n):
        gx, gy = xs[k - 1], rows[k] - 30
        g = d.gate("XOR", gx, gy, "XOR")
        d.text(30, rows[k] + 4, f"G{n - 1 - k}", anchor="end", size=13, bold=True)
        d.wire((36, rows[k]), g["b"])
        if k == 1:
            tx = gx - 40
            d.dot(tx, rows[0])
            d.wire((tx, rows[0]), (tx, g["a"][1]), g["a"])
        else:
            ox, oy = prev_out
            bx = ox + 20
            d.dot(bx, oy)
            d.wire((bx, oy), (bx, g["a"][1]), g["a"])
        # output continues to the right-hand label column
        ox, oy = g["out"]
        d.wire((ox, oy), (x_end, oy))
        d.text(x_end + 8, oy + 4, f"B{n - 1 - k}", anchor="start", size=13, bold=True)
        prev_out = g["out"]
    return d


_LOGIC_GATE_KINDS = {"AND": "AND", "NAND": "NAND", "OR": "OR", "NOR": "NOR", "XOR": "XOR", "XNOR": "XNOR"}


def build_logic_diagram(sub_type, width=4):
    """Returns a LogicDiagram for a CIRCUIT_DATABASE digital circuit, or None if unsupported."""
    if sub_type in _LOGIC_GATE_KINDS:
        return _build_single_gate(_LOGIC_GATE_KINDS[sub_type])
    builders = {
        "NOT": _build_not,
        "half_adder": _build_half_adder,
        "full_adder": _build_full_adder,
        "half_subtractor": _build_half_subtractor,
        "full_subtractor": _build_full_subtractor,
        "mux_2_1": _build_mux_2_1,
    }
    if sub_type in builders:
        return builders[sub_type]()
    if sub_type == "bin_to_gray":
        return _build_bin_to_gray(width)
    if sub_type == "gray_to_bin":
        return _build_gray_to_bin(width)
    return None


def get_digital_boolean_expressions(sub_type, width=4):
    """Boolean / functional description lines for a digital circuit (plain ASCII)."""
    simple = {
        "AND": ["Y = A AND B"],
        "NAND": ["Y = NOT (A AND B)"],
        "OR": ["Y = A OR B"],
        "NOR": ["Y = NOT (A OR B)"],
        "XOR": ["Y = A XOR B"],
        "XNOR": ["Y = NOT (A XOR B)"],
        "NOT": ["Y = NOT A"],
        "half_adder": ["Sum = A XOR B", "Carry = A AND B"],
        "full_adder": ["Sum = A XOR B XOR Cin", "Carry-out = (A AND B) OR (Cin AND (A XOR B))"],
        "half_subtractor": ["Difference = A XOR B", "Borrow = (NOT A) AND B"],
        "full_subtractor": ["Difference = A XOR B XOR Bin",
                            "Borrow-out = ((NOT A) AND B) OR ((NOT (A XOR B)) AND Bin)"],
        "mux_2_1": ["Y = ((NOT S) AND I0) OR (S AND I1)"],
    }
    if sub_type in simple:
        return list(simple[sub_type])
    n = max(2, min(int(width), 4))
    if sub_type == "bin_to_gray":
        return [f"G{n - 1} = B{n - 1}"] + [f"G{i} = B{i + 1} XOR B{i}" for i in range(n - 2, -1, -1)]
    if sub_type == "gray_to_bin":
        return [f"B{n - 1} = G{n - 1}"] + [f"B{i} = B{i + 1} XOR G{i}" for i in range(n - 2, -1, -1)]
    return []


def render_diagram_svg(d):
    """Serialises a LogicDiagram to a standalone, responsive SVG string."""
    w, h = d.width, d.height
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:g} {h:g}" width="100%" '
           f'style="max-width:{w:g}px;height:auto;" role="img" aria-label="{html.escape(d.title)}">',
           f'<title>{html.escape(d.title)}</title>']
    for it in d.items:
        kind = it[0]
        if kind == "poly":
            pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in it[1])
            out.append(f'<polyline points="{pts}" fill="none" stroke="{_DIAG_WIRE}" stroke-width="1.8" '
                       f'stroke-linejoin="round" stroke-linecap="round"/>')
        elif kind == "path":
            cmds, closed = it[1], it[2]
            seg = []
            for c in cmds:
                if c[0] in ("M", "L"):
                    seg.append(f"{c[0]}{c[1]:.1f},{c[2]:.1f}")
                elif c[0] == "Q":
                    seg.append(f"Q{c[1]:.1f},{c[2]:.1f} {c[3]:.1f},{c[4]:.1f}")
                elif c[0] == "Z":
                    seg.append("Z")
            fill = _DIAG_FILL if closed else "none"
            out.append(f'<path d="{" ".join(seg)}" fill="{fill}" stroke="{_DIAG_STROKE}" stroke-width="2" '
                       f'stroke-linejoin="round"/>')
        elif kind == "circle":
            _, cx, cy, r, filled = it
            fill = _DIAG_WIRE if filled else "#ffffff"
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:g}" fill="{fill}" stroke="{_DIAG_STROKE}" stroke-width="1.8"/>')
        elif kind == "rect":
            _, x, y, rw, rh = it
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{rw:.1f}" height="{rh:.1f}" fill="{_DIAG_FILL}" '
                       f'stroke="{_DIAG_STROKE}" stroke-width="2"/>')
        elif kind == "text":
            _, x, y, s, anchor, size, bold, color = it
            weight = "700" if bold else "400"
            out.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="Helvetica, Arial, sans-serif" '
                       f'font-size="{size:g}" font-weight="{weight}" fill="{color}">{html.escape(s)}</text>')
    out.append("</svg>")
    return "".join(out)


def render_diagram_drawing(d, max_width):
    """Builds a vector ReportLab Drawing of the diagram, scaled to fit max_width (points)."""
    from reportlab.graphics.shapes import Drawing, Path, PolyLine, Circle, String, Rect
    sc = min(max_width / d.width, 1.35)
    dr = Drawing(d.width * sc, d.height * sc)
    hx = colors.HexColor

    def X(x):
        return x * sc

    def Y(y):
        return (d.height - y) * sc

    for it in d.items:
        kind = it[0]
        if kind == "poly":
            flat = []
            for x, y in it[1]:
                flat += [X(x), Y(y)]
            dr.add(PolyLine(flat, strokeColor=hx(_DIAG_WIRE), strokeWidth=1.3, strokeLineJoin=1, strokeLineCap=1))
        elif kind == "path":
            cmds, closed = it[1], it[2]
            p = Path(fillColor=hx(_DIAG_FILL) if closed else None, strokeColor=hx(_DIAG_STROKE),
                     strokeWidth=1.5, strokeLineJoin=1)
            cur = (0.0, 0.0)
            for c in cmds:
                if c[0] == "M":
                    p.moveTo(X(c[1]), Y(c[2])); cur = (c[1], c[2])
                elif c[0] == "L":
                    p.lineTo(X(c[1]), Y(c[2])); cur = (c[1], c[2])
                elif c[0] == "Q":
                    cx, cy, ex, ey = c[1], c[2], c[3], c[4]
                    c1 = (cur[0] + 2.0 / 3.0 * (cx - cur[0]), cur[1] + 2.0 / 3.0 * (cy - cur[1]))
                    c2 = (ex + 2.0 / 3.0 * (cx - ex), ey + 2.0 / 3.0 * (cy - ey))
                    p.curveTo(X(c1[0]), Y(c1[1]), X(c2[0]), Y(c2[1]), X(ex), Y(ey)); cur = (ex, ey)
                elif c[0] == "Z":
                    p.closePath()
            dr.add(p)
        elif kind == "circle":
            _, cx, cy, r, filled = it
            dr.add(Circle(X(cx), Y(cy), r * sc, fillColor=hx(_DIAG_WIRE) if filled else colors.white,
                          strokeColor=hx(_DIAG_STROKE), strokeWidth=1.3))
        elif kind == "rect":
            _, x, y, rw, rh = it
            dr.add(Rect(X(x), Y(y + rh), rw * sc, rh * sc, fillColor=hx(_DIAG_FILL),
                        strokeColor=hx(_DIAG_STROKE), strokeWidth=1.5))
        elif kind == "text":
            _, x, y, s, anchor, size, bold, color = it
            dr.add(String(X(x), Y(y), s, fontName="Helvetica-Bold" if bold else "Helvetica",
                          fontSize=size * sc, textAnchor=anchor, fillColor=hx(color)))
    return dr



# ==============================================================================
# STUDENT REPORT: validation, report data preparation, offline digital diagnosis,
# PDF generation and e-mail delivery (pure functions - no Streamlit dependency,
# so they can be unit tested; the UI lives in the "Generate Report" page).
# ==============================================================================
REPORT_YEAR_OPTIONS = ["First Year", "Second Year", "Third Year", "Final Year", "Other (type below)"]
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'\-]+@[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?)*\.[A-Za-z]{2,}$")
_DIVISION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 \-]{0,9}$")
_CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")


def _clean_text(value, max_len=120):
    """Trims, collapses whitespace and strips control characters (no header/PDF injection)."""
    text = _CTRL_RE.sub(" ", str(value if value is not None else ""))
    return re.sub(r"\s+", " ", text).strip()[:max_len]


def validate_student_details(raw):
    """Validates the Student Details form. Returns (clean_dict, errors_dict).
    errors maps a field name to a message; an empty dict means the details are valid."""
    raw = raw or {}
    errors = {}
    name = _clean_text(raw.get("name"), 80)
    if not name:
        errors["name"] = "Student name is required."
    elif not re.search(r"[A-Za-z]", name):
        errors["name"] = "Student name must contain letters."

    year_choice = _clean_text(raw.get("year"), 40)
    if year_choice.startswith("Other"):
        year = _clean_text(raw.get("year_other"), 40)
        if not year:
            errors["year"] = "Please type the academic year (e.g. 2025-26)."
    else:
        year = year_choice
        if not year or year.startswith(("-", "\u2014")):
            year = ""
            errors["year"] = "Select the year / academic year."

    division = _clean_text(raw.get("division"), 10)
    if not division:
        errors["division"] = "Division is required (e.g. A, B, C)."
    elif not _DIVISION_RE.match(division):
        errors["division"] = "Division may contain only letters, digits, space or hyphen (max 10 characters)."

    email = _clean_text(raw.get("email"), 254).replace(" ", "")
    if not email:
        errors["email"] = "Email ID is required."
    elif len(email) > 254 or not _EMAIL_RE.match(email) or ".." in email:
        errors["email"] = "Enter a valid email address (for example name@college.edu)."

    clean = {
        "name": name, "year": year, "division": division.upper() if division else "", "email": email,
        "roll_no": _clean_text(raw.get("roll_no"), 40),
        "college": _clean_text(raw.get("college"), 120),
        "branch": _clean_text(raw.get("branch"), 80),
        "report_title": _clean_text(raw.get("report_title"), 120),
    }
    return clean, errors


def sanitize_filename_part(text, max_len=40):
    part = re.sub(r"[^A-Za-z0-9]+", "_", str(text or "")).strip("_")
    return (part[:max_len].strip("_")) or "NA"


def build_report_filename(student_name, circuit_name, when):
    return (f"NEXUS_Test_Report_{sanitize_filename_part(student_name)}_"
            f"{sanitize_filename_part(circuit_name)}_{when.strftime('%Y%m%d_%H%M%S')}.pdf")


def new_test_id(ts):
    return f"NX-{ts.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"


# ------------------------------------------------------------------------------
# OFFLINE DIGITAL DIAGNOSIS (local, deterministic - works without Gemini/internet)
# ------------------------------------------------------------------------------
def build_offline_digital_diagnosis(analysis):
    """Builds the offline diagnosis text blocks from a compute_digital_analysis() result."""
    status = analysis["det_status"]
    cells = analysis.get("cells", [])
    th = analysis.get("thresholds", {"v_il": 0.8, "v_ih": 2.0})
    findings, actions, limits = [], [], []

    if status == "PASS":
        summary = (f"All {analysis['total_cells']} required output cells were measured with valid logic levels and every "
                   f"measured output matches the expected truth table.")
    elif status == "FAIL":
        summary = (f"All required output cells have valid measurements, but {analysis['mismatches']} of "
                   f"{analysis['total_cells']} outputs do not match the expected truth table.")
    else:
        summary = (f"A complete determination is not possible: {analysis['missing_cells']} required cell(s) are missing and "
                   f"{analysis['invalid_cells']} cell(s) have an invalid logic level. "
                   f"Only {analysis['valid_cells']} of {analysis['total_cells']} cells ({analysis['coverage_pct']:.1f} %) are valid.")

    def _lim(items, n=20):
        shown = items[:n]
        if len(items) > n:
            shown.append(f"... and {len(items) - n} more.")
        return shown

    mism = [c for c in cells if c["status"] == "MISMATCH"]
    for c in _lim([f"MISMATCH - Row {c['row']} ({c['inputs']}), output {c['output']}: expected {c['expected']}, "
                   f"measured logic {c['state']} ({c['voltage']})." for c in mism]):
        findings.append(c)
    inval = [c for c in cells if c["status"] == "INVALID"]
    for c in _lim([f"INVALID - Row {c['row']} ({c['inputs']}), output {c['output']}: measured {c['voltage']}, which is "
                   f"not a valid logic level (logic 0 <= {th['v_il']} V, logic 1 >= {th['v_ih']} V)." for c in inval]):
        findings.append(c)
    miss = [c for c in cells if c["status"] == "MISSING"]
    if miss:
        for c in _lim([f"MISSING - Row {c['row']} ({c['inputs']}), output {c['output']}: no measurement saved." for c in miss]):
            findings.append(c)

    # pattern hints (hypotheses derived only from the measured states)
    outputs = []
    for c in cells:
        if c["output"] not in outputs:
            outputs.append(c["output"])
    for out in outputs:
        valid = [c for c in cells if c["output"] == out and c["status"] in ("MATCH", "MISMATCH")]
        if len(valid) >= 2:
            states = {c["state"] for c in valid}
            expected_vals = {c["expected"] for c in valid}
            if len(states) == 1 and len(expected_vals) > 1:
                findings.append(f"PATTERN - Output {out} reads logic {next(iter(states))} in all {len(valid)} valid "
                                f"measurements although the expected value changes (possible stuck-at condition: open/short "
                                f"on the output, missing supply, or heavy loading). This is a hypothesis, not a confirmed fault.")
            elif all(c["status"] == "MISMATCH" for c in valid):
                findings.append(f"PATTERN - Output {out} is the opposite of the expected value in all {len(valid)} valid "
                                f"measurements (possible inverted output, wrong gate/IC type, or swapped wiring). "
                                f"This is a hypothesis, not a confirmed fault.")
    if not findings:
        findings.append("No mismatches, invalid levels or missing cells were found.")

    if status == "PASS":
        actions.append("No corrective action is required. Keep this report as the record of the verified truth table.")
    else:
        if miss or inval:
            actions.append("Measure every missing cell and re-measure every INVALID cell, then run ANALYSE again.")
        if mism or inval:
            actions.append("Confirm the input switches/pins are set exactly to the input combination of the row being measured.")
            actions.append("Check the supply voltage and common ground between the circuit and the ESP32 sensor input.")
            actions.append("Check the IC pin-out and wiring against the circuit diagram in this report.")
            actions.append("Measure the output pin directly; look for floating inputs, loading on the output, or a damaged IC.")
        actions.append("Re-test the failing rows after each correction.")
    limits.append("This diagnosis is a local rule-based comparison of the saved measurements with the expected truth table; "
                  "it identifies where the outputs differ but cannot confirm the physical cause.")
    if status == "INCOMPLETE":
        limits.append("The result is INCOMPLETE: it must not be read as PASS or FAIL until all cells are measured and valid.")
    return {"summary": summary, "findings": findings, "actions": actions, "limitations": limits}


# ------------------------------------------------------------------------------
# REPORT DATA PREPARATION (from a stored test record)
# ------------------------------------------------------------------------------
def _gemini_block_digital(res):
    st_ = res.get("gemini_status", "NOT_RUN")
    if st_ == "OK" and res.get("gemini_report"):
        return {"status": "GENERATED", "text": res["gemini_report"], "note": "AI-generated engineering interpretation for this exact test."}
    if st_ == "NO_KEY":
        return {"status": "NOT RUN", "text": "", "note": "Gemini was not run for this test (no API key configured at analysis time)."}
    if st_ == "ERROR":
        return {"status": "UNAVAILABLE", "text": "", "note": str(res.get("gemini_error") or "Gemini request failed.")}
    return {"status": "NOT RUN", "text": "", "note": "Gemini analysis has not been run for this test."}


def build_report_data(record, student, generated_at=None):
    """Converts a stored test record into the plain data structure used by the PDF/e-mail.
    Only values stored in the record are used - nothing is measured or invented here."""
    generated_at = generated_at or datetime.datetime.now()
    res = record["result"]
    data = {
        "kind": record["kind"], "student": dict(student), "generated_at": generated_at,
        "test_id": record["test_id"], "circuit": record["circuit"], "category": record["category"],
        "test_time": record["timestamp"], "warnings": [],
    }
    if record["kind"] == "digital":
        info = res.get("circuit_info", {})
        sub = info.get("sub_type")
        width = res.get("bit_width", 4)
        data.update({
            "overall_status": res["det_status"],
            "circuit_type": info.get("type", "N/A"),
            "description": info.get("description", "N/A"),
            "boolean_expressions": get_digital_boolean_expressions(sub, width),
            "diagram": build_logic_diagram(sub, width),
            "analysis": res,
            "expected_rows": res.get("expected_rows", []),
            "offline": build_offline_digital_diagnosis(res),
            "gemini": _gemini_block_digital(res),
        })
        if res["det_status"] == "INCOMPLETE":
            data["warnings"].append(f"INCOMPLETE test: {res['missing_cells']} missing and {res['invalid_cells']} invalid cell(s). "
                                    f"The circuit can be neither passed nor failed.")
        if data["diagram"] is None:
            data["warnings"].append("No logic diagram is available for this circuit type.")
    else:
        snap = res["sensor"]
        eng = str(res.get("engine", "GEMINI"))
        if eng.upper().startswith("GEMINI"):
            gem = {"status": "GENERATED", "text": res.get("text", ""), "note": "AI-generated interpretation for this exact test."}
        else:
            gem = {"status": "NOT USED", "text": res.get("text", ""),
                   "note": f"Gemini was not used for this test; the diagnosis below was produced by the {eng} (rule-based, local)."}
        data.update({
            "overall_status": res["status"], "info": res.get("circuit_info", {}), "targets": res["targets"],
            "snapshot": snap, "deviations": res.get("deviations", {}), "source": res.get("source", "N/A"),
            "engine": eng, "fault_probability": res.get("fault_probability"), "confidence": res.get("confidence"),
            "structured": res.get("structured"), "gemini": gem,
        })
        if res.get("source") == "HELD":
            data["warnings"].append("Input voltage/current were HELD values captured earlier; output values were live readings.")
        if str(snap.get("frequency", 0)) in ("0", "0.0") and str(snap.get("temperature", 0)) in ("0", "0.0"):
            data["warnings"].append("Frequency and temperature are 0: the sensor may not report them.")
    return data


def report_summary_lines(data):
    """Short plain-text outcome summary (used by the e-mail body and the UI)."""
    if data["kind"] == "digital":
        a = data["analysis"]
        return [f"Overall result: {data['overall_status']}",
                f"Coverage: {a['coverage_pct']:.1f}% ({a['valid_cells']}/{a['total_cells']} valid output cells)",
                f"Correct matches: {a['correct_matches']}, mismatches: {a['mismatches']}, "
                f"missing: {a['missing_cells']}, invalid: {a['invalid_cells']}"]
    s = data["snapshot"]
    return [f"Overall result: {data['overall_status']}",
            f"Measured input {_fmt(s.get('input_v'))} V / {_fmt(s.get('input_i'))} A, "
            f"output {_fmt(s.get('output_v'))} V / {_fmt(s.get('output_i'))} A, efficiency {_fmt(s.get('efficiency'))} %"]


def build_report_conclusion(data):
    if data["kind"] == "digital":
        a = data["analysis"]
        if data["overall_status"] == "PASS":
            return (f"The {data['circuit']} produced the expected output in all {a['total_cells']} required truth-table cells "
                    f"(coverage 100 %). The circuit passed the test.")
        if data["overall_status"] == "FAIL":
            return (f"The {data['circuit']} was fully measured but {a['mismatches']} of {a['total_cells']} outputs differ from the "
                    f"expected truth table. The circuit failed the test.")
        return (f"The test of the {data['circuit']} is INCOMPLETE ({a['coverage_pct']:.1f} % coverage, {a['missing_cells']} missing, "
                f"{a['invalid_cells']} invalid). No PASS or FAIL decision can be made until every cell is measured with a valid logic level.")
    s = data["snapshot"]
    return (f"For the {data['circuit']}, the measured output voltage was {_fmt(s.get('output_v'))} V against a target of "
            f"{_fmt(data['targets'].get('target_output_voltage'))} V. The deterministic comparison of the four measured quantities "
            f"with their targets gives the overall result {data['overall_status']}.")


# ------------------------------------------------------------------------------
# PDF GENERATION
# ------------------------------------------------------------------------------
_STATUS_COLORS = {"PASS": "#1a8f4c", "NORMAL": "#1a8f4c", "MATCH": "#1a8f4c", "FAIL": "#c62828", "MISMATCH": "#c62828",
                  "INCOMPLETE": "#b26a00", "WARNING": "#b26a00", "INVALID": "#b26a00", "MISSING": "#b26a00"}


def _make_numbered_canvas(meta):
    from reportlab.pdfgen import canvas as rl_canvas

    class _NumberedCanvas(rl_canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_pages = []

        def showPage(self):
            self._saved_pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved_pages)
            for state in self._saved_pages:
                self.__dict__.update(state)
                self._decorate(total)
                super().showPage()
            super().save()

        def _decorate(self, total):
            w, h = A4
            self.setStrokeColor(colors.HexColor("#9fb3c8"))
            self.setLineWidth(0.5)
            self.line(18 * mm, 15 * mm, w - 18 * mm, 15 * mm)
            self.setFont("Helvetica", 7.5)
            self.setFillColor(colors.HexColor("#4a5a6e"))
            self.drawString(18 * mm, 10.5 * mm, _pdf_plain(f"NEXUS Test Report | {meta['student']} | Test ID {meta['test_id']}"))
            self.drawRightString(w - 18 * mm, 10.5 * mm, f"Page {self._pageNumber} of {total}")
            self.drawString(18 * mm, 6.5 * mm, _pdf_plain(f"Report generated: {meta['generated']}"))
            self.drawRightString(w - 18 * mm, h - 10 * mm, "NEXUS - AI-Based Electronic Circuit Tester")

    return _NumberedCanvas


def _pdf_plain(value):
    """latin-1 safe text WITHOUT XML escaping (for canvas.drawString)."""
    text = str(value if value is not None else "N/A")
    for k, v in _PDF_CHAR_MAP.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")


def _md_to_para(line):
    """Escapes a Gemini/markdown line for ReportLab and converts **bold**."""
    safe = _pdf_safe(line)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)


def _text_block(text, body, head, bullet):
    out = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line:
            out.append(Spacer(1, 3))
            continue
        m = re.match(r"^#{1,6}\s*(.*)$", line)
        if m:
            out.append(Paragraph(_md_to_para(m.group(1)), head))
        elif re.match(r"^[\*\-]\s+", line):
            out.append(Paragraph("- " + _md_to_para(re.sub(r"^[\*\-]\s+", "", line)), bullet))
        else:
            clean = line.replace("```", "")
            out.append(Paragraph(_md_to_para(clean), body))
    return out


def generate_test_report_pdf(data):
    """Creates the professional A4 test report and returns the PDF bytes."""
    from reportlab.platypus import PageBreak, CondPageBreak, KeepTogether
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            title=f"NEXUS Electronic Circuit Test Report - {_pdf_plain(data['circuit'])}",
                            author="NEXUS - AI-Based Electronic Circuit Tester",
                            subject=f"Test ID {data['test_id']}")
    CW = 174 * mm
    base = getSampleStyleSheet()
    S = {
        "band1": ParagraphStyle("band1", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=11, textColor=colors.HexColor("#9fd8ff"), leading=14),
        "band2": ParagraphStyle("band2", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=20, textColor=colors.white, leading=24),
        "band3": ParagraphStyle("band3", parent=base["Normal"], fontName="Helvetica", fontSize=9.5, textColor=colors.HexColor("#d6e6f5"), leading=12),
        "h1": ParagraphStyle("h1", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=13, textColor=colors.HexColor("#0b3c5d"), spaceBefore=10, spaceAfter=5),
        "h2": ParagraphStyle("h2", parent=base["Heading3"], fontName="Helvetica-Bold", fontSize=10.5, textColor=colors.HexColor("#0b3c5d"), spaceBefore=7, spaceAfter=3),
        "body": ParagraphStyle("body", parent=base["Normal"], fontName="Helvetica", fontSize=9, leading=12),
        "small": ParagraphStyle("small", parent=base["Normal"], fontName="Helvetica", fontSize=8.5, leading=11),
        "cell": ParagraphStyle("cell", parent=base["Normal"], fontName="Helvetica", fontSize=8.3, leading=10.5),
        "cellb": ParagraphStyle("cellb", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8.3, leading=10.5),
        "cellh": ParagraphStyle("cellh", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8.3, leading=10.5, textColor=colors.white),
        "note": ParagraphStyle("note", parent=base["Normal"], fontName="Helvetica-Oblique", fontSize=8, leading=10.5, textColor=colors.HexColor("#4a5a6e")),
        "bullet": ParagraphStyle("bullet", parent=base["Normal"], fontName="Helvetica", fontSize=9, leading=12, leftIndent=10),
        "mono": ParagraphStyle("mono", parent=base["Normal"], fontName="Courier", fontSize=9, leading=12, leftIndent=6),
    }

    def P(text, style="body"):
        return Paragraph(_pdf_safe(text), S[style])

    def tbl(rows, widths, header=True, align_right_from=None, extra=None, repeat=1):
        t = Table(rows, colWidths=widths, repeatRows=repeat if header else 0)
        style = [("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9fb3c8")),
                 ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                 ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                 ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
        if header:
            style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b3c5d"))]
            style += [("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f7fb")])]
        if align_right_from is not None:
            style.append(("ALIGN", (align_right_from, 0), (-1, -1), "RIGHT"))
        if extra:
            style += extra
        t.setStyle(TableStyle(style))
        return t

    def kv_rows(pairs):
        return [[Paragraph(f"<b>{_pdf_safe(a)}</b>", S["cell"]), Paragraph(_pdf_safe(b), S["cell"])] for a, b in pairs]

    def head_row(labels):
        return [Paragraph(_pdf_safe(x), S["cellh"]) for x in labels]

    stu = data["student"]
    status = data["overall_status"]
    scol = colors.HexColor(_STATUS_COLORS.get(status, "#0b3c5d"))
    el = []

    # ------------------------------------------------------------ cover / page 1
    title_txt = stu.get("report_title") or "Electronic Circuit Test Report"
    band = Table([[Paragraph("NEXUS - AI-BASED ELECTRONIC CIRCUIT TESTER", S["band1"])],
                  [Paragraph(_pdf_safe(title_txt) if stu.get("report_title") else "Electronic Circuit Test Report", S["band2"])],
                  [Paragraph(_pdf_safe(f"{data['category']} | {data['circuit']}"), S["band3"])]], colWidths=[CW])
    band.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0b3c5d")),
                              ("LEFTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (0, 0), 12),
                              ("BOTTOMPADDING", (0, -1), (-1, -1), 12)]))
    el += [band, Spacer(1, 10)]
    badge = Table([[Paragraph("<b>OVERALL TEST RESULT</b>", S["cellb"]),
                    Paragraph(f"<font color='white'><b>{_pdf_safe(status)}</b></font>", ParagraphStyle("badge", parent=S["body"], fontSize=15, leading=18, alignment=1))]],
                  colWidths=[CW * 0.6, CW * 0.4])
    badge.setStyle(TableStyle([("BACKGROUND", (1, 0), (1, 0), scol), ("BOX", (0, 0), (-1, -1), 0.8, scol),
                               ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    el += [badge, Spacer(1, 6)]

    el.append(P("Student Details", "h1"))
    srows = [("Student name", stu["name"]), ("Year / Academic year", stu["year"]), ("Division", stu["division"]),
             ("Email ID", stu["email"])]
    for key, lab in (("roll_no", "Roll number"), ("college", "College"), ("branch", "Branch")):
        if stu.get(key):
            srows.append((lab, stu[key]))
    el.append(tbl(kv_rows(srows), [55 * mm, 119 * mm], header=False))

    el.append(P("Test Information", "h1"))
    irows = [("Circuit category", data["category"]), ("Circuit name", data["circuit"]), ("Test ID", data["test_id"]),
             ("Test date and time", data["test_time"].strftime("%Y-%m-%d %H:%M:%S")),
             ("Report generated", data["generated_at"].strftime("%Y-%m-%d %H:%M:%S"))]
    if data["kind"] == "analogue":
        irows.append(("Analysis source", f"{data['source']} ({'held input + live output' if data['source'] == 'HELD' else 'all live'})"))
        irows.append(("Analysis engine", data["engine"]))
    else:
        irows.append(("Circuit type", data["circuit_type"]))
    el.append(tbl(kv_rows(irows), [55 * mm, 119 * mm], header=False))

    el.append(P("Results at a glance", "h1"))
    glance = [P(x) for x in report_summary_lines(data)]
    el += glance
    el.append(Spacer(1, 4))
    el.append(P("How to read this report: MEASURED values come from the NEXUS ESP32 sensor telemetry; EXPECTED values come from the "
                "circuit database / configured targets or the deterministic truth table; CALCULATED values are derived by NEXUS; "
                "AI-GENERATED text is an interpretation and never changes the deterministic result.", "note"))

    # ------------------------------------------------------------ results
    el.append(CondPageBreak(110 * mm))
    el.append(P("Circuit and Test Results", "h1"))
    if data["kind"] == "digital":
        a = data["analysis"]
        el.append(P("Circuit description", "h2"))
        el.append(P(data["description"]))
        if data["boolean_expressions"]:
            el.append(P("Boolean expression / functional description", "h2"))
            for ex in data["boolean_expressions"]:
                el.append(Paragraph(_pdf_safe(ex), S["mono"]))
        el.append(P("Logic gate / circuit diagram", "h2"))
        if data.get("diagram") is not None:
            try:
                el.append(KeepTogether([render_diagram_drawing(data["diagram"], CW),
                                        P(f"Figure 1: {data['circuit']} (generated from the same circuit definition used by the NEXUS dashboard).", "note")]))
            except Exception as exc:  # never fail the whole report because of the figure
                el.append(P(f"Diagram could not be rendered: {exc}", "note"))
        else:
            el.append(P("No diagram is available for this circuit.", "note"))

        rows_exp = data.get("expected_rows", [])
        if rows_exp:
            el.append(P("Expected truth table", "h2"))
            cols = list(rows_exp[0].keys())
            body = [head_row(cols)] + [[Paragraph(_pdf_safe(r.get(c, "")), S["cell"]) for c in cols] for r in rows_exp]
            el.append(tbl(body, [CW / len(cols)] * len(cols)))

        stats = [head_row(["Quantity", "Value"])] + kv_rows([
            ("Total required output cells", a["total_cells"]), ("Valid measured cells", a["valid_cells"]),
            ("Correct matches", a["correct_matches"]), ("Mismatches", a["mismatches"]),
            ("Missing cells", a["missing_cells"]), ("Invalid logic levels", a["invalid_cells"]),
            ("Test coverage", f"{a['coverage_pct']:.1f} %"),
            ("Logic thresholds", f"Logic 0 <= {a['thresholds']['v_il']} V, logic 1 >= {a['thresholds']['v_ih']} V, otherwise INVALID"),
            ("Deterministic result", a["det_status"])])
        el.append(KeepTogether([P("Summary statistics", "h2"), tbl(stats, [70 * mm, 104 * mm])]))

        el.append(P("Measured results - cell-by-cell comparison", "h2"))
        crow = [head_row(["Row", "Input combination", "Output", "Expected", "Measured V", "State", "Result"])]
        extra = []
        for i, c in enumerate(a.get("cells", []), start=1):
            crow.append([Paragraph(str(c["row"]), S["cell"]), Paragraph(_pdf_safe(c["inputs"]), S["cell"]),
                         Paragraph(_pdf_safe(c["output"]), S["cell"]), Paragraph(str(c["expected"]), S["cell"]),
                         Paragraph(_pdf_safe(c["voltage"]), S["cell"]), Paragraph(_pdf_safe(c["state"]), S["cell"]),
                         Paragraph(_pdf_safe(c["status"]), S["cellb"])])
            extra.append(("TEXTCOLOR", (6, i), (6, i), colors.HexColor(_STATUS_COLORS.get(c["status"], "#000000"))))
        el.append(tbl(crow, [12 * mm, 52 * mm, 20 * mm, 20 * mm, 26 * mm, 20 * mm, 24 * mm], extra=extra))
        el.append(Spacer(1, 4))
        el.append(P("Result key: MATCH = measured logic equals expected; MISMATCH = measured logic differs; INVALID = voltage between "
                    "the thresholds or unusable; MISSING = no measurement saved.", "note"))
    else:
        info = data["info"]
        el.append(P("Circuit description", "h2"))
        el.append(P(info.get("description", "N/A")))
        el.append(Paragraph(f"<b>Components:</b> {_pdf_safe(info.get('components', 'N/A'))}", S["small"]))
        el.append(Paragraph(f"<b>Circuit topology:</b> {_pdf_safe(info.get('diagram', 'N/A'))}", S["small"]))
        for pr in info.get("probes", []) or []:
            el.append(Paragraph(f"&nbsp;&nbsp;Probe {_pdf_safe(pr.get('step'))} - {_pdf_safe(pr.get('name'))}: {_pdf_safe(pr.get('loc'))}", S["small"]))
        snap, tg, dev = data["snapshot"], data["targets"], data["deviations"]
        el.append(P("Expected vs measured electrical parameters", "h2"))

        def devtxt(k):
            return f"{_fmt(dev.get(k))} %" if k in dev else "N/A"
        rows = [head_row(["Parameter", "Expected (target)", "Measured", "Deviation"]),
                [P("Input voltage", "cell"), P(f"{_fmt(tg.get('target_input_voltage'))} V", "cell"), P(f"{_fmt(snap.get('input_v'))} V", "cell"), P(devtxt("Input Voltage"), "cell")],
                [P("Output voltage", "cell"), P(f"{_fmt(tg.get('target_output_voltage'))} V", "cell"), P(f"{_fmt(snap.get('output_v'))} V", "cell"), P(devtxt("Output Voltage"), "cell")],
                [P("Input current", "cell"), P(f"{_fmt(tg.get('target_input_current'))} A", "cell"), P(f"{_fmt(snap.get('input_i'))} A", "cell"), P(devtxt("Input Current"), "cell")],
                [P("Output current", "cell"), P(f"{_fmt(tg.get('target_output_current'))} A", "cell"), P(f"{_fmt(snap.get('output_i'))} A", "cell"), P(devtxt("Output Current"), "cell")]]
        el.append(tbl(rows, [50 * mm, 42 * mm, 42 * mm, 40 * mm], align_right_from=1))
        el.append(P("Expected = configured/database target. Measured = ESP32 sensor reading. Deviation = |measured - target| / target x 100 (calculated).", "note"))
        el.append(P("Calculated parameters", "h2"))
        calc = [head_row(["Quantity", "Value"]),
                [P("Input power", "cell"), P(f"{_fmt(snap.get('power_in'))} W", "cell")],
                [P("Output power", "cell"), P(f"{_fmt(snap.get('power_out'))} W", "cell")],
                [P("Efficiency", "cell"), P(f"{_fmt(snap.get('efficiency'))} %  (database nominal {info.get('exp_eff', 'N/A')} %)", "cell")],
                [P("Voltage drop (Vin - Vout)", "cell"), P(f"{_fmt(snap.get('v_drop'))} V", "cell")],
                [P("Frequency", "cell"), P(f"{_fmt(snap.get('frequency'), 1)} Hz", "cell")],
                [P("Temperature", "cell"), P(f"{_fmt(snap.get('temperature'), 1)} C", "cell")],
                [P("Circuit health", "cell"), P(f"{snap.get('health', 'N/A')} %", "cell")]]
        el.append(tbl(calc, [70 * mm, 104 * mm]))
        el.append(P("Test outcome", "h2"))
        fp, cf = data.get("fault_probability"), data.get("confidence")
        outc = [head_row(["Deterministic result", "Fault probability (AI/rule estimate)", "Diagnosis confidence (AI/rule estimate)"]),
                [P(status, "cellb"), P(f"{fp} %" if fp is not None else "N/A", "cell"), P(f"{cf} %" if cf is not None else "N/A", "cell")]]
        el.append(tbl(outc, [50 * mm, 62 * mm, 62 * mm]))
        el.append(P("Deterministic rule: PASS when every parameter is within +/-5 % of its target, WARNING above 5 % up to 10 %, FAIL above 10 %.", "note"))

    # ------------------------------------------------------------ diagnosis
    el.append(CondPageBreak(90 * mm))
    el.append(P("Diagnosis and Recommendations", "h1"))
    el.append(P("Deterministic test result (calculated from measured data)", "h2"))
    det_text = (data["offline"]["summary"] if data["kind"] == "digital" else
                "Computed by comparing the measured input/output voltage and current with their targets.")
    el.append(Paragraph(f"<b>{_pdf_safe(status)}</b> - {_pdf_safe(det_text)}", S["body"]))
    if data["kind"] == "digital":
        off = data["offline"]
        el.append(P("Offline digital diagnosis (local truth-table comparison)", "h2"))
        el.append(P("Produced locally by NEXUS; no internet or Gemini access is needed.", "note"))
        for f in off["findings"]:
            el.append(Paragraph("- " + _pdf_safe(f), S["bullet"]))
        el.append(P("Suggested actions", "h2"))
        for f in off["actions"]:
            el.append(Paragraph("- " + _pdf_safe(f), S["bullet"]))
    gem = data["gemini"]
    if data["kind"] == "digital" or gem["status"] == "GENERATED":
        title = "Gemini AI diagnosis"
    else:
        title = f"Diagnosis by {data.get('engine', 'offline engine')} (Gemini not used)"
    el.append(CondPageBreak(45 * mm))
    el.append(P(f"{title} - status: {gem['status']}", "h2"))
    el.append(P(gem["note"], "note"))
    if gem["text"]:
        el += _text_block(gem["text"], S["small"], S["cellb"], ParagraphStyle("b2", parent=S["small"], leftIndent=10))
    if data["kind"] == "analogue" and data.get("structured"):
        stp = data["structured"].get("recommended_steps") or []
        if stp:
            el.append(P("Recommended troubleshooting steps", "h2"))
            for i, x in enumerate(stp, 1):
                el.append(Paragraph(f"{i}. {_pdf_safe(x)}", S["bullet"]))
    el.append(P("Warnings and limitations", "h2"))
    wl = list(data["warnings"]) + (data["offline"]["limitations"] if data["kind"] == "digital" else
                                   ["AI/rule-based fault probabilities are estimates from electrical values only."])
    wl.append("AI-generated text is an interpretation and does not change the deterministic result.")
    for w_ in wl:
        el.append(Paragraph("- " + _pdf_safe(w_), S["bullet"]))
    el.append(P("Conclusion", "h2"))
    el.append(P(build_report_conclusion(data)))

    meta = {"student": stu["name"], "test_id": data["test_id"],
            "generated": data["generated_at"].strftime("%Y-%m-%d %H:%M:%S")}
    doc.build(el, canvasmaker=_make_numbered_canvas(meta))
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


# ------------------------------------------------------------------------------
# E-MAIL DELIVERY (SMTP, credentials from environment variables / Streamlit secrets)
# ------------------------------------------------------------------------------
SMTP_SETTING_KEYS = ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_SENDER_EMAIL", "SMTP_SECURITY"]


def get_smtp_config(env=None, secrets=None):
    """Builds the SMTP configuration. Environment variables take priority over secrets."""
    env, secrets = env or {}, secrets or {}

    def pick(key, default=""):
        val = env.get(key)
        if val in (None, ""):
            val = secrets.get(key)
        return str(val).strip() if val not in (None, "") else default
    cfg = {"host": pick("SMTP_HOST"), "port_raw": pick("SMTP_PORT", "587"), "username": pick("SMTP_USERNAME"),
           "password": pick("SMTP_PASSWORD"), "sender": pick("SMTP_SENDER_EMAIL"),
           "security": pick("SMTP_SECURITY", "").lower()}
    if not cfg["sender"] and _EMAIL_RE.match(cfg["username"] or ""):
        cfg["sender"] = cfg["username"]
    try:
        cfg["port"] = int(cfg["port_raw"])
    except ValueError:
        cfg["port"] = None
    if cfg["security"] not in ("ssl", "starttls"):
        cfg["security"] = "ssl" if cfg["port"] == 465 else "starttls"
    return cfg


def smtp_config_problems(cfg):
    """Returns a list of missing/invalid setting names (empty list == configured)."""
    problems = []
    if not cfg.get("host"):
        problems.append("SMTP_HOST")
    if cfg.get("port") is None or not (0 < cfg["port"] < 65536):
        problems.append("SMTP_PORT (must be a number)")
    if not cfg.get("username"):
        problems.append("SMTP_USERNAME")
    if not cfg.get("password"):
        problems.append("SMTP_PASSWORD")
    if not cfg.get("sender") or not _EMAIL_RE.match(cfg["sender"]):
        problems.append("SMTP_SENDER_EMAIL")
    return problems


def build_report_email(sender, recipient, data, pdf_bytes, filename):
    """Builds the e-mail (plain text + PDF attachment). Sender comes ONLY from server config."""
    stu = data["student"]
    circuit = _clean_text(data["circuit"], 80)
    msg = EmailMessage()
    msg["Subject"] = f"NEXUS Electronic Circuit Test Report \u2014 {circuit}"
    msg["From"] = _clean_text(sender, 254)
    msg["To"] = _clean_text(recipient, 254)
    lines = [f"Dear {stu['name']},", "",
             "Please find attached your NEXUS Electronic Circuit Test Report.", "",
             f"Student name : {stu['name']}", f"Year         : {stu['year']}", f"Division     : {stu['division']}",
             f"Circuit      : {data['circuit']}", f"Test date    : {data['test_time'].strftime('%Y-%m-%d %H:%M:%S')}",
             f"Test ID      : {data['test_id']}", ""] + report_summary_lines(data) + [
             "", "The PDF report is attached to this message.", "",
             "-- NEXUS - AI-Based Electronic Circuit Tester"]
    msg.set_content("\n".join(_CTRL_RE.sub(" ", str(l)) for l in lines))
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=_clean_text(filename, 200))
    return msg


def send_report_email(cfg, message, smtp_cls=None, smtp_ssl_cls=None, timeout=20):
    """Sends `message`. Returns (ok, human_readable_message). Never raises."""
    smtp_cls = smtp_cls or smtplib.SMTP
    smtp_ssl_cls = smtp_ssl_cls or smtplib.SMTP_SSL
    recipient = message["To"]
    problems = smtp_config_problems(cfg)
    if problems:
        return False, "Email is not configured. Missing/invalid: " + ", ".join(problems) + "."
    try:
        ctx = ssl.create_default_context()
        if cfg["security"] == "ssl":
            server = smtp_ssl_cls(cfg["host"], cfg["port"], timeout=timeout, context=ctx)
        else:
            server = smtp_cls(cfg["host"], cfg["port"], timeout=timeout)
        with server:
            if cfg["security"] != "ssl":
                server.ehlo()
                server.starttls(context=ctx)
                server.ehlo()
            server.login(cfg["username"], cfg["password"])
            refused = server.send_message(message)
        if refused:
            return False, f"The SMTP server refused the recipient address ({recipient})."
        return True, (f"Email sent successfully: the SMTP server accepted the message for delivery to {recipient}. "
                      f"SMTP acceptance does not guarantee final inbox delivery - please also check the spam/junk folder.")
    except smtplib.SMTPAuthenticationError:
        return False, "Email failed: SMTP authentication was rejected. Check SMTP_USERNAME / SMTP_PASSWORD (an app password may be required)."
    except smtplib.SMTPRecipientsRefused:
        return False, f"Email failed: the recipient address {recipient} was refused by the server."
    except smtplib.SMTPSenderRefused:
        return False, "Email failed: the sender address was refused. Check SMTP_SENDER_EMAIL."
    except smtplib.SMTPConnectError:
        return False, "Email failed: could not connect to the SMTP server. Check SMTP_HOST / SMTP_PORT."
    except (socket.timeout, TimeoutError):
        return False, "Email failed: the SMTP server timed out."
    except ssl.SSLError:
        return False, "Email failed: a secure (TLS/SSL) connection could not be established. Check SMTP_PORT / SMTP_SECURITY."
    except smtplib.SMTPException as exc:
        return False, f"Email failed: SMTP error ({type(exc).__name__})."
    except OSError as exc:
        return False, f"Email failed: network error ({type(exc).__name__}). Check the connection and SMTP_HOST."
    except Exception as exc:  # last resort - never crash the app
        return False, f"Email failed: unexpected error ({type(exc).__name__})."



def report_revision_key(student_clean, record):
    """Fingerprint of everything a generated report depends on (details + exact test record)."""
    payload = json.dumps({"student": student_clean, "test_id": record["test_id"], "kind": record["kind"]}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_smtp_settings():
    """Reads SMTP settings from environment variables, falling back to Streamlit secrets.
    Never logs or displays the values."""
    secrets_map = {}
    try:
        for key in SMTP_SETTING_KEYS:
            if key in st.secrets:
                secrets_map[key] = st.secrets[key]
    except Exception:
        secrets_map = {}
    return get_smtp_config(dict(os.environ), secrets_map)


def generate_history_pdf(record):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm,
                             leftMargin=18 * mm, rightMargin=18 * mm)
    styles = getSampleStyleSheet()
    elements = []

    user_question = record.get("User Question", "")

    elements.append(Paragraph("NEXUS AI ELECTRONIC CIRCUIT TEST REPORT", styles["Title"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>Date:</b> {record.get('Date', 'N/A')}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Time:</b> {record.get('Time', 'N/A')}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Circuit:</b> {record.get('Circuit', 'N/A')}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Status:</b> {record.get('Status', 'N/A')}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Input Voltage:</b> {record.get('Input Voltage (V)', 'N/A')}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Output Voltage:</b> {record.get('Output Voltage (V)', 'N/A')}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Efficiency:</b> {record.get('Efficiency %', 'N/A')}", styles["Normal"]))
    elements.append(Spacer(1, 10))

    if user_question:
        elements.append(Paragraph("<b>User Question:</b>", styles["Normal"]))
        safe_q = str(user_question).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
        elements.append(Paragraph(safe_q, styles["Normal"]))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("<b>Gemini AI Response:</b>", styles["Normal"]))
    else:
        elements.append(Paragraph("<b>AI Answer / Diagnosis:</b>", styles["Normal"]))

    diag_text = record.get("AI Answer / Diagnosis", "N/A")
    safe_diag = str(diag_text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
    elements.append(Paragraph(safe_diag, styles["Normal"]))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

# ------------------------------------------------------------------------------
# 4. HOLLYWOOD-QUALITY AI OPERATING SYSTEM INTERFACE & GRAPHICS
# ------------------------------------------------------------------------------
st.set_page_config(page_title="NEXUS AI OS v2.3", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")
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
    box-shadow: 0 0 12px currentColor;
    animation: pulseGlow 1.8s infinite;
}

@keyframes pulseGlow {
    0% { transform: scale(0.9); }
    50% { transform: scale(1.3); }
    100% { transform: scale(0.9); }
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
                ESP32 LINK STANDBY | MQTT INITIALIZING | DATABASE READY | GEMINI STANDBY
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
# TOP HEADER HUD CONTROL BAR (AUTOMATIC 1-SECOND REFRESH FRAGMENT)
# ------------------------------------------------------------------------------
@st.fragment(run_every="1s")
def render_os_header():
    now = datetime.datetime.now()

    if get_mqtt_connection_status() == "Connected":
        mqtt_display, mqtt_color = "CONNECTED", "#00ff87"
    else:
        mqtt_display, mqtt_color = "DISCONNECTED", "#ff0055"

    esp_state, _esp_age = get_esp32_status()
    if esp_state == "ONLINE":
        esp_display, esp_color = "ONLINE", "#00ff87"
    elif esp_state == "WAITING":
        esp_display, esp_color = "WAITING FOR DATA", "#ffb703"
    else:
        esp_display, esp_color = "OFFLINE", "#ff0055"

    st.markdown(f"""
    <div class="os-header-bar">
        <div class="sys-tag"><span class="os-indicator-dot" style="background-color:{mqtt_color}; color:{mqtt_color};"></span> <b>SYSTEM:</b> NEXUS AI OS</div>
        <div><b>DATE:</b> {now.strftime("%Y-%m-%d")}</div>
        <div><b>TIME:</b> {now.strftime("%H:%M:%S")}</div>
        <div><b>ESP32:</b> <span style="color:{esp_color};">{esp_display}</span></div>
        <div><b>MQTT:</b> <span style="color:{mqtt_color};">{mqtt_display}</span></div>
        <div><b>GEMINI:</b> <span style="color:#00ff87;">ACTIVE</span></div>
        <div><b>CPU:</b> 12.4%</div>
        <div><b>RAM:</b> 3.2 GB</div>
        <div><b>FPS:</b> 60.0</div>
    </div>
    """, unsafe_allow_html=True)

render_os_header()

# Sidebar System Menu
st.sidebar.markdown('<div style="font-family:Orbitron; font-size:1.1rem; color:#00f2fe; margin-bottom:15px; font-weight:700;">⚡ OS NAVIGATION</div>', unsafe_allow_html=True)
pages = ["Home", "Circuit Type", "Configuration", "Probe Guide", "Testing Dashboard", "Digital Circuit Tester", "Generate Report", "History", "Settings", "About"]
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
        <p style="font-size: 1.0rem; color:#00f2fe;"><b>COMPONENTS:</b> {curr_circuit.get('components', curr_circuit.get('diagram', 'N/A'))}</p>
        <p><b>SCHEMATIC VECTOR:</b> <code style="color:#00ff87; background:rgba(0,0,0,0.6); padding:6px 12px; border-radius:4px; border:1px solid rgba(0,255,135,0.3);">{curr_circuit['diagram']}</code></p>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    c_h1, c_h2 = st.columns(2)
    with c_h1:
        if st.button("INITIALIZE SYSTEM CONFIGURATION →", use_container_width=True):
            if st.session_state.selected_category == "Digital Circuits":
                st.session_state.page = "Digital Circuit Tester"
            else:
                st.session_state.page = "Configuration"
            st.rerun()
    with c_h2:
        if st.button("LAUNCH DIGITAL TESTER MODULE →", use_container_width=True):
            st.session_state.selected_category = "Digital Circuits"
            st.session_state.page = "Digital Circuit Tester"
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
                <p style="color:#00ff87;"><b>Details:</b> {c_info.get('components', c_info.get('diagram', 'N/A'))}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"LOAD {c_name.upper()}", key=f"btn_{c_name}"):
                set_active_circuit(st.session_state.selected_category, c_name)
                if st.session_state.selected_category == "Digital Circuits":
                    st.session_state.page = "Digital Circuit Tester"
                else:
                    st.session_state.page = "Configuration"
                st.rerun()

# ------------------------------------------------------------------------------
# STEP 3: CONFIGURATION
# ------------------------------------------------------------------------------
elif st.session_state.page == "Configuration":
    if st.session_state.selected_category == "Digital Circuits":
        st.session_state.page = "Digital Circuit Tester"
        st.rerun()
    st.header(f"⚙️ TARGET CONFIGURATION - {st.session_state.selected_circuit}")
    st.markdown('<div class="os-card">', unsafe_allow_html=True)
    
    st.markdown(f"**HARDWARE MATRIX SPEC:** `{curr_circuit.get('components', 'N/A')}`")
    st.markdown("<hr style='border:0; height:1px; background: rgba(0,242,254,0.2);'>", unsafe_allow_html=True)
    
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
    if st.session_state.selected_category == "Digital Circuits":
        st.session_state.page = "Digital Circuit Tester"
        st.rerun()
    st.header(f"📍 SENSOR PROBE CALIBRATION - {st.session_state.selected_circuit}")
    st.info(f"🧩 **ACTIVE LAYOUT CONFIGURATION**: {curr_circuit.get('components', 'N/A')}")
    for probe in curr_circuit.get("probes", []):
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
# STEP 5: TESTING DASHBOARD (AUTOMATIC 1-SECOND LIVE TELEMETRY REFRESH)
# ------------------------------------------------------------------------------
elif st.session_state.page == "Testing Dashboard":
    if st.session_state.selected_category == "Digital Circuits":
        st.session_state.page = "Digital Circuit Tester"
        st.rerun()
    st.header(f"📊 LIVE AI OS DIAGNOSTIC MATRIX - {st.session_state.selected_circuit}")
    st.caption(f"Hardware Topology Specs: {curr_circuit.get('components', 'N/A')}")
    
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

    if is_data_held() and st.session_state.held_input_data.get("circuit") != st.session_state.selected_circuit:
        release_testing_data()

    held_now = is_data_held()
    with st.container(border=True):
        st.markdown('<div style="text-align:center; font-family:Orbitron, sans-serif; color:#00f2fe; letter-spacing:2px; font-weight:700; margin-bottom:8px;">TEST ACQUISITION CONTROL</div>', unsafe_allow_html=True)
        ctl1, ctl2, ctl3 = st.columns(3)
        with ctl1:
            st.button("⏸ HOLD", key="hold_data_btn", on_click=hold_testing_data, disabled=held_now, use_container_width=True)
        with ctl2:
            st.button("▶ RELEASE", key="release_data_btn", on_click=release_testing_data, disabled=not held_now, use_container_width=True)
        with ctl3:
            analyze_clicked = st.button("🤖 ANALYZE WITH GEMINI", key="analyze_gemini_btn", use_container_width=True)

        if held_now:
            cap_str = st.session_state.hold_timestamp.strftime("%H:%M:%S") if st.session_state.hold_timestamp else "—"
            st.markdown(f'<div style="text-align:center; font-family:Orbitron, sans-serif;"><span style="color:#ffb703; font-weight:700;">STATUS: INPUT V/I HELD</span><br><span style="color:#c8d6e5; font-size:0.85rem;">CAPTURED: {cap_str} | OUTPUT LIVE</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="text-align:center; font-family:Orbitron, sans-serif;"><span style="color:#00ff87; font-weight:700;">STATUS: LIVE</span></div>', unsafe_allow_html=True)

    if st.session_state.get("hold_error"):
        st.warning(st.session_state.hold_error)

    @st.fragment(run_every="1s")
    def render_live_testing_dashboard():
        sensor_data = get_testing_sensor_data(curr_circuit)
        data_is_held = sensor_data["source"] == "HELD"
        frozen_note = ' | <span style="color:#ffb703;">❄ INPUT V/I FROZEN — OUTPUT LIVE — MQTT STILL RECEIVING</span>' if data_is_held else ''
        sensor_status, _ = evaluate_pass_fail_status(active_targets, sensor_data)

        last_time_str = datetime.datetime.now().strftime("%H:%M:%S")
        st.markdown(f"""
        <div style="text-align: right; font-family: 'Orbitron', sans-serif; font-size: 0.75rem; color: #00f2fe; margin-bottom: 8px;">
            📡 LAST MQTT SYNC: <span style="color:#00ff87;">{last_time_str}</span> | PACKETS PROCESSED: <span style="color:#00ff87;">{get_mqtt_packet_count()}</span>{frozen_note}
        </div>
        """, unsafe_allow_html=True)

        st.subheader("📡 SENSOR ACQUISITION METRICS")
        g1, g2, g3 = st.columns(3)
        with g1:
            st.plotly_chart(create_circular_gauge(("HELD " if data_is_held else "") + "Input Voltage", sensor_data['input_v'], max(30.0, active_targets['target_input_voltage'] * 1.5), "V", "#00f2fe"), use_container_width=True)
        with g2:
            st.plotly_chart(create_circular_gauge("Live Output Voltage", sensor_data['output_v'], max(30.0, active_targets['target_output_voltage'] * 1.5), "V", "#00ff87"), use_container_width=True)
        with g3:
            st.plotly_chart(create_circular_gauge("Circuit Health", sensor_data['health'], 100, "%", "#ff0055" if sensor_data['health'] < 80 else "#00ff87"), use_container_width=True)

        st.markdown('<div class="os-card">', unsafe_allow_html=True)
        col5, col6, col7, col8 = st.columns(4)
        col5.metric("HELD INPUT CURRENT" if data_is_held else "INPUT CURRENT", f"{sensor_data['input_i']:.3f} A")
        col6.metric("LIVE OUTPUT CURRENT", f"{sensor_data['output_i']:.3f} A")
        col7.metric("FREQUENCY", f"{sensor_data['frequency']:.1f} Hz")
        col8.metric("TEMPERATURE", f"{sensor_data['temperature']:.1f} °C")
        col9, col10, col11, col12 = st.columns(4)
        col9.metric("INPUT POWER", f"{sensor_data['power_in']:.2f} W")
        col10.metric("OUTPUT POWER", f"{sensor_data['power_out']:.2f} W")
        col11.metric("VOLTAGE DROP", f"{sensor_data['v_drop']:.2f} V")
        col12.metric("TEST RESULT", sensor_status)
        st.markdown('</div>', unsafe_allow_html=True)

        render_nexus_telemetry(sensor_data)

    render_live_testing_dashboard()

    mqtt_status = get_mqtt_status()
    latest_packet = get_latest_sensor_packet()
    valid_mqtt_data = latest_packet is not None
    data_available = valid_mqtt_data or is_data_held()

    st.markdown("---")
    st.subheader("🤖 GEMINI AI DIAGNOSIS ENGINE")

    if analyze_clicked:
        run_gemini_analysis(curr_circuit, active_targets)

    if st.session_state.last_gemini_result is not None:
        render_analysis_result(st.session_state.last_gemini_result)
    elif not data_available:
        st.info("No valid sensor data available for analysis. Waiting for ESP32 telemetry.")
    else:
        st.caption("Press ⏸ HOLD to freeze Input V/I only (optional), then 🤖 ANALYZE WITH GEMINI.")

    st.markdown("---")
    st.subheader("💬 GEMINI AI OS COPILOT TERMINAL")
    
    user_query = st.text_input("INPUT DIRECTIVE FOR GEMINI AI:", placeholder="e.g., Explain causes for voltage degradation on diode branch", key="dashboard_gemini_query")
    
    if st.button("EXECUTE DIRECTIVE", key="dashboard_ask_btn"):
        if user_query.strip():
            client = get_gemini_client()
            if client:
                try:
                    with st.spinner("Processing neural query..."):
                        sensor_data_snapshot = get_testing_sensor_data(curr_circuit) if data_available else {}
                        context_prompt = f"""
                        Circuit Name: {st.session_state.selected_circuit}
                        Active User Targets: {active_targets}
                        Sensor Telemetry (source: {sensor_data_snapshot.get('source', 'N/A')}): {sensor_data_snapshot}
                        MQTT Status: {mqtt_status}
                        
                        User Question: {user_query}
                        
                        Provide a concise, expert engineering response comparing measurements to active target specs.
                        """
                        response = client.models.generate_content(
                            model='gemini-3.6-flash',
                            contents=context_prompt
                        )
                        answer = response.text

                        gemini_status_snapshot = None
                        try:
                            if data_available:
                                gemini_status_snapshot, _ = evaluate_pass_fail_status(active_targets, sensor_data_snapshot)
                        except Exception:
                            gemini_status_snapshot = None
                        save_gemini_to_history(
                            st.session_state.selected_circuit,
                            user_query,
                            answer,
                            metrics=sensor_data_snapshot,
                            status=gemini_status_snapshot
                        )

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
# STEP 6: DIGITAL CIRCUIT TESTER MODULE
# ------------------------------------------------------------------------------
elif st.session_state.page == "Digital Circuit Tester":
    st.header("🔬 NEXUS DIGITAL CIRCUITS TESTING MODULE")
    st.caption("Verify logic gates, code converters, arithmetic circuits, and the mandatory 2:1 multiplexer using live single-voltage sensor telemetry.")

    digital_circuits_list = list(CIRCUIT_DATABASE["Digital Circuits"].keys())
    selected_dig_ckt = st.selectbox("SELECT DIGITAL CIRCUIT", digital_circuits_list, index=0, key="dig_ckt_select")
    st.session_state.selected_category = "Digital Circuits"
    st.session_state.selected_circuit = selected_dig_ckt
    ckt_info = CIRCUIT_DATABASE["Digital Circuits"][selected_dig_ckt]

    st.markdown(f"""
    <div class="os-card">
        <h3 style="color:#00f2fe; margin-top:0;">⚡ {selected_dig_ckt}</h3>
        <p><b>Description:</b> {ckt_info['description']}</p>
        <p><b>Schematic:</b> <code style="color:#00ff87; background:rgba(0,0,0,0.6); padding:4px 10px;">{ckt_info['diagram']}</code></p>
    </div>
    """, unsafe_allow_html=True)

    bit_width = 4
    if ckt_info.get("sub_type") in ["bin_to_gray", "gray_to_bin"]:
        bit_width = st.selectbox("Select Bit Width", [2, 3, 4], index=2, key="dig_bit_width_select")
        st.session_state.digital_bit_width = bit_width

    with st.expander("⚙️ Logic Voltage Threshold Configuration"):
        th_col1, th_col2 = st.columns(2)
        with th_col1:
            v_il = st.number_input("Max Voltage for Logic 0 (V_IL)", value=0.8, step=0.1, key="thresh_vil")
        with th_col2:
            v_ih = st.number_input("Min Voltage for Logic 1 (V_IH)", value=2.0, step=0.1, key="thresh_vih")
        st.session_state.digital_thresholds = {"v_il": v_il, "v_ih": v_ih}

    @st.fragment(run_every="1s")
    def render_digital_live_sensor():
        packet, _ = get_latest_packet_and_time()
        live_v = None
        try:
            if packet is not None:
                live_v = float(packet.get("output_voltage", packet.get("output_v")))
                if not math.isfinite(live_v):
                    live_v = None
        except (TypeError, ValueError):
            live_v = None
        logic_state = classify_digital_voltage(live_v if live_v is not None else float("nan"), st.session_state.digital_thresholds["v_il"], st.session_state.digital_thresholds["v_ih"])
        
        live_v_txt = f"{live_v:.3f} V" if live_v is not None else "NO DATA"
        logic_txt = logic_state if live_v is not None else "—"
        state_color = "#00ff87" if logic_state == "1" else ("#00f2fe" if logic_state == "0" else "#ff0055")
        st.markdown(f"""
        <div class="os-card" style="border-left: 5px solid {state_color} !important; display: flex; justify-content: space-around; align-items: center; text-align: center;">
            <div>
                <div style="font-family: Orbitron; font-size: 0.75rem; color: #8fa3b8;">LATEST SENSOR VOLTAGE</div>
                <div style="font-family: Orbitron; font-size: 1.8rem; color: #ffffff;">{live_v_txt}</div>
            </div>
            <div>
                <div style="font-family: Orbitron; font-size: 0.75rem; color: #8fa3b8;">CLASSIFIED LOGIC STATE</div>
                <div style="font-family: Orbitron; font-size: 1.8rem; color: {state_color}; font-weight: 700;">{logic_txt}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return live_v, logic_state

    render_digital_live_sensor()
    expected_df = generate_expected_truth_table(selected_dig_ckt, width=st.session_state.digital_bit_width)
    input_cols, output_cols, possible_outputs = get_digital_table_layout(expected_df)

    # If the truth-table shape changed (e.g. converter bit width), previously saved cells
    # no longer describe the same rows/outputs -> clear only this circuit's test data.
    cur_sig = digital_table_signature(expected_df)
    prev_sig = st.session_state.digital_table_sigs.get(selected_dig_ckt)
    if prev_sig is not None and prev_sig != cur_sig:
        st.session_state.digital_measurements[selected_dig_ckt] = {}
        digital_invalidate_analysis(selected_dig_ckt)
        st.session_state.digital_selected_cells.pop(selected_dig_ckt, None)
        st.session_state.digital_save_notice.pop(selected_dig_ckt, None)
        st.warning("Truth-table size changed (bit width). Saved measurements for this circuit were cleared because they no longer match the table.")
    st.session_state.digital_table_sigs[selected_dig_ckt] = cur_sig

    st.markdown("### 🧩 Circuit Diagram / Logic Gate Diagram")
    try:
        _diag = build_logic_diagram(ckt_info.get("sub_type"), st.session_state.digital_bit_width)
        if _diag is None:
            st.warning(f"No logic diagram is defined for {selected_dig_ckt}.")
            st.code(ckt_info.get("diagram", ""), language=None)
        else:
            st.components.v1.html(
                f'<div style="background:#ffffff; border-radius:10px; padding:10px; box-sizing:border-box;">{render_diagram_svg(_diag)}</div>',
                height=int(_diag.height) + 40, scrolling=True)
            _exprs = get_digital_boolean_expressions(ckt_info.get("sub_type"), st.session_state.digital_bit_width)
            if _exprs:
                st.code("\n".join(_exprs), language=None)
    except Exception as _diag_err:
        st.warning(f"The circuit diagram could not be rendered ({_diag_err}). Schematic summary: {ckt_info.get('diagram', 'N/A')}")

    st.markdown("### 📋 Expected Truth Table (Deterministic)")
    st.dataframe(expected_df, use_container_width=True)

    st.markdown("### 🎮 Interactive Measured Truth Table")
    st.info("Click any output cell in the grid below to select it as the save destination, then press **SAVE CELL** to store the live sensor voltage there. Cells can be measured in any order.")

    if selected_dig_ckt not in st.session_state.digital_measurements:
        st.session_state.digital_measurements[selected_dig_ckt] = {}
    ckt_meas = st.session_state.digital_measurements[selected_dig_ckt]

    # Active destination (kept in session state so it survives reruns)
    sel = st.session_state.digital_selected_cells.get(selected_dig_ckt)
    if sel is None or sel[0] >= len(expected_df) or sel[1] not in possible_outputs:
        sel = (0, possible_outputs[0])
        st.session_state.digital_selected_cells[selected_dig_ckt] = sel
    sel_row, sel_out = sel

    dest_slot = st.empty()
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        save_clicked = st.button("💾 SAVE CELL", key="dig_save_btn", use_container_width=True)
    with btn_col2:
        reset_clicked = st.button("🔄 RESET CURRENT DIGITAL TEST", key="dig_reset_btn", use_container_width=True)

    sel_inputs_txt = ", ".join(f"{c}={expected_df.iloc[sel_row][c]}" for c in input_cols)

    if save_clicked:
        # Read the live sensor NOW (never reuse a displayed/stale value, never fabricate 0 V).
        saved_v, saved_pkt_time, save_err = get_fresh_output_measurement()
        if save_err:
            st.session_state.digital_save_notice[selected_dig_ckt] = (
                "error", f"Cannot save to Row {sel_row}, Output '{sel_out}': {save_err} Nothing was saved.")
        else:
            th = st.session_state.digital_thresholds
            saved_state = classify_digital_voltage(saved_v, th["v_il"], th["v_ih"])
            # Only the selected cell is written; every other saved cell is left untouched.
            ckt_meas[(sel_row, sel_out)] = {
                "voltage": saved_v,
                "logic_state": saved_state,
                "timestamp": datetime.datetime.now(),
                "sensor_packet_time": saved_pkt_time,
            }
            # Test data changed -> any previous analysis/Gemini report is now out of date.
            digital_invalidate_analysis(selected_dig_ckt)
            level = "success" if saved_state in ("0", "1") else "warning"
            state_txt = f"Logic {saved_state}" if saved_state in ("0", "1") else "INVALID logic level (between V_IL and V_IH)"
            st.session_state.digital_save_notice[selected_dig_ckt] = (
                level, f"Saved {saved_v:.3f} V ({state_txt}) to Row {sel_row} [{sel_inputs_txt}], Output '{sel_out}'.")

    if reset_clicked:
        # Clears ONLY this circuit's digital measurements, selection and analysis.
        st.session_state.digital_measurements[selected_dig_ckt] = {}
        ckt_meas = st.session_state.digital_measurements[selected_dig_ckt]
        digital_invalidate_analysis(selected_dig_ckt)
        sel_row, sel_out = 0, possible_outputs[0]
        st.session_state.digital_selected_cells[selected_dig_ckt] = (sel_row, sel_out)
        sel_inputs_txt = ", ".join(f"{c}={expected_df.iloc[sel_row][c]}" for c in input_cols)
        st.session_state.digital_save_notice[selected_dig_ckt] = ("success", "Digital measurements for this circuit were reset.")

    notice = st.session_state.digital_save_notice.get(selected_dig_ckt)
    if notice:
        if notice[0] == "success":
            st.success(notice[1])
        elif notice[0] == "warning":
            st.warning(notice[1])
        else:
            st.error(notice[1])

    existing_m = ckt_meas.get((sel_row, sel_out))
    existing_txt = (f"currently saved: {existing_m['voltage']:.3f} V (state {existing_m['logic_state']}) - will be overwritten"
                    if existing_m is not None else "currently empty")
    dest_slot.markdown(f"""
    <div class="os-card" style="border-left: 5px solid #00f2fe !important;">
        <div style="font-family: Orbitron; font-size: 0.75rem; color: #8fa3b8;">ACTIVE SAVE DESTINATION</div>
        <div style="font-family: Orbitron; font-size: 1.1rem; color: #ffffff;">Row {sel_row} &nbsp;|&nbsp; {html.escape(sel_inputs_txt)} &nbsp;|&nbsp; Output <span style="color:#00ff87;">{html.escape(str(sel_out))}</span></div>
        <div style="color:#8fa3b8;">{html.escape(existing_txt)}</div>
    </div>
    """, unsafe_allow_html=True)

    # ---- Clickable measured truth-table grid (one button per output cell) ----
    grid_weights = [0.6] + [1.0] * len(input_cols) + [1.6] * len(possible_outputs)
    hdr_cols = st.columns(grid_weights)
    hdr_cols[0].markdown("**Row**")
    for ci, c in enumerate(input_cols):
        hdr_cols[1 + ci].markdown(f"**{c}**")
    for oi, out_l in enumerate(possible_outputs):
        hdr_cols[1 + len(input_cols) + oi].markdown(f"**{out_l} (measured)**")

    for i in range(len(expected_df)):
        row_cols = st.columns(grid_weights)
        row_cols[0].markdown(f"`{i}`")
        for ci, c in enumerate(input_cols):
            row_cols[1 + ci].markdown(f"`{expected_df.iloc[i][c]}`")
        for oi, out_l in enumerate(possible_outputs):
            m_info = ckt_meas.get((i, out_l))
            is_selected = (i == sel_row and out_l == sel_out)
            if m_info is not None:
                cell_label = f"{m_info['logic_state']} · {m_info['voltage']:.2f} V"
            else:
                cell_label = "—"
            if is_selected:
                cell_label = "🎯 " + cell_label
            row_cols[1 + len(input_cols) + oi].button(
                cell_label,
                key=f"dig_cell_{selected_dig_ckt}_{i}_{out_l}",
                type="primary" if is_selected else "secondary",
                use_container_width=True,
                on_click=digital_select_cell,
                args=(selected_dig_ckt, i, out_l),
            )

    st.caption("Measured values are shown here as saved. The PASS / FAIL / INCOMPLETE result is calculated only when you press ANALYSE DIGITAL CIRCUIT.")

    # ---- ANALYSE: the only place the deterministic result and Gemini report are produced ----
    analyse_clicked = st.button("🤖 ANALYSE DIGITAL CIRCUIT", key="dig_gemini_btn", use_container_width=True)

    if analyse_clicked:
        result = compute_digital_analysis(selected_dig_ckt, expected_df, dict(ckt_meas))
        # Everything the student report needs is frozen into this analysis (exact test, circuit, table and cells).
        result["test_id"] = new_test_id(result["analysed_at"])
        result["circuit_info"] = {k: ckt_info.get(k) for k in ("type", "sub_type", "description", "diagram")}
        result["expected_rows"] = expected_df.to_dict(orient="records")
        result["bit_width"] = st.session_state.digital_bit_width
        result["measurements_snapshot"] = copy.deepcopy(dict(ckt_meas))
        client = get_gemini_client()
        if not client:
            result["gemini_status"] = "NO_KEY"
            result["gemini_error"] = "Gemini API key missing. Configure the key in the Settings tab to get an engineering diagnosis."
        else:
            with st.spinner("Sending complete truth table dataset and measurements to Gemini..."):
                measured_list = []
                for (m_row, m_out), m_val in sorted(ckt_meas.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
                    if m_row >= len(expected_df) or m_out not in possible_outputs:
                        continue
                    exp_col_nm = f"Expected {m_out}" if f"Expected {m_out}" in expected_df.columns else m_out
                    measured_list.append({
                        "row": m_row,
                        "inputs": ", ".join(f"{c}={expected_df.iloc[m_row][c]}" for c in input_cols),
                        "output": m_out,
                        "expected_logic": int(expected_df.iloc[m_row][exp_col_nm]),
                        "measured_voltage": m_val["voltage"],
                        "measured_logic_state": m_val["logic_state"],
                        "timestamp": str(m_val["timestamp"]),
                    })
                dataset = {
                    "circuit_name": selected_dig_ckt,
                    "circuit_description": ckt_info['description'],
                    "logic_thresholds": result["thresholds"],
                    "expected_truth_table": expected_df.to_dict(orient="records"),
                    "measured_truth_table": measured_list,
                    "non_matching_cells": result["details"],
                    "measurement_summary": {
                        "total_cells": result["total_cells"],
                        "valid_cells": result["valid_cells"],
                        "correct_matches": result["correct_matches"],
                        "missing_cells": result["missing_cells"],
                        "invalid_cells": result["invalid_cells"],
                        "mismatches": result["mismatches"],
                        "coverage_percent": result["coverage_pct"]
                    },
                    "deterministic_status": result["det_status"]
                }
                det_status = result["det_status"]
                prompt = f"""You are analysing a digital circuit test performed by the NEXUS Electronic Circuit Tester. Use the supplied expected truth table, actual measured truth table, raw voltages, classified logic states, and comparison results.
The expected truth table was calculated deterministically by the application. Do not replace or recalculate it as though it were unknown.
Analyse every provided row and output. Identify mismatches by input combination and output label. Explain plausible causes, such as incorrect wiring, incorrect input configuration, a defective gate or IC, unsuitable supply voltage, floating inputs, loading, sensor calibration errors, or incorrect logic thresholds, but distinguish hypotheses from confirmed evidence.
Do not invent measurements. Do not change missing or invalid readings into zeros. Do not claim that an unmeasured cell passed. Do not override the application's deterministic PASS, FAIL, or INCOMPLETE result ({det_status}).
If measurements are incomplete, explicitly explain that the diagnosis is limited. Base every conclusion on the supplied test data, and state when the evidence is insufficient to identify a specific fault.

DATASET:
{json.dumps(dataset, indent=2, default=str)}

Respond with a professional engineering diagnostic report.
"""
                try:
                    response = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=prompt
                    )
                    report_text = getattr(response, "text", None)
                    if report_text:
                        result["gemini_report"] = report_text
                        result["gemini_status"] = "OK"
                    else:
                        result["gemini_status"] = "ERROR"
                        result["gemini_error"] = "Gemini returned an empty response."
                except Exception as e:
                    result["gemini_status"] = "ERROR"
                    result["gemini_error"] = f"Gemini API Error: {e}"
        st.session_state.digital_analysis[selected_dig_ckt] = result
        st.session_state.analysis_records.append({
            "test_id": result["test_id"], "kind": "digital", "circuit": selected_dig_ckt,
            "category": "Digital Circuits", "timestamp": result["analysed_at"], "result": copy.deepcopy(result),
        })
        st.session_state.report_selected_test = result["test_id"]
        if result["gemini_status"] == "OK":
            speak_text("Digital circuit analysis complete.")

    # ---- Persisted analysis display (current circuit + current table only) ----
    analysis = st.session_state.digital_analysis.get(selected_dig_ckt)
    if analysis is not None and analysis.get("signature") != cur_sig:
        digital_invalidate_analysis(selected_dig_ckt)
        analysis = None

    if analysis is not None:
        det_status = analysis["det_status"]
        status_color = "#00ff87" if det_status == "PASS" else ("#ff0055" if det_status == "FAIL" else "#ffb703")
        st.markdown(f"""
        <div class="os-card" style="border-left: 5px solid {status_color} !important;">
            <h4 style="color:{status_color}; margin-top:0;">DETERMINISTIC TEST RESULT: {det_status}</h4>
            <p><b>Measurement Coverage:</b> {analysis['coverage_pct']:.1f}% ({analysis['valid_cells']}/{analysis['total_cells']} valid required cells)</p>
            <p style="color:#8fa3b8;">Analysed at {analysis['analysed_at'].strftime('%Y-%m-%d %H:%M:%S')} using V_IL={analysis['thresholds']['v_il']} V, V_IH={analysis['thresholds']['v_ih']} V. Saving or overwriting any cell invalidates this result.</p>
        </div>
        """, unsafe_allow_html=True)

        mt1, mt2, mt3, mt4 = st.columns(4)
        mt1.metric("Deterministic Result", det_status)
        mt2.metric("Measurement Coverage", f"{analysis['coverage_pct']:.1f}%")
        mt3.metric("Total Required Output Cells", analysis["total_cells"])
        mt4.metric("Valid Measured Cells", analysis["valid_cells"])
        mt5, mt6, mt7, mt8 = st.columns(4)
        mt5.metric("Correct Matches", analysis["correct_matches"])
        mt6.metric("Mismatches", analysis["mismatches"])
        mt7.metric("Missing Cells", analysis["missing_cells"])
        mt8.metric("Invalid Logic Levels", analysis["invalid_cells"])

        if analysis.get("cells"):
            with st.expander("📊 Truth table results: expected vs measured (MATCH / MISMATCH / INVALID / MISSING)", expanded=True):
                _cells_df = pd.DataFrame(analysis["cells"]).rename(columns={
                    "row": "Row", "inputs": "Inputs", "output": "Output", "expected": "Expected",
                    "voltage": "Measured V", "state": "Measured State", "status": "Result"})
                st.dataframe(_cells_df, use_container_width=True)
        if analysis["details"]:
            with st.expander(f"Cells needing attention ({len(analysis['details'])})"):
                st.dataframe(pd.DataFrame(analysis["details"]), use_container_width=True)

        _off = build_offline_digital_diagnosis(analysis)
        st.markdown("### 🧮 Offline Digital Diagnosis (local - works without Gemini)")
        _find_html = "".join(f"<li>{html.escape(x)}</li>" for x in _off["findings"])
        _act_html = "".join(f"<li>{html.escape(x)}</li>" for x in _off["actions"])
        _lim_html = " ".join(html.escape(x) for x in _off["limitations"])
        st.markdown(f"""
        <div class="os-card" style="border-left: 5px solid #9d4edd !important;">
            <p><b>{html.escape(_off['summary'])}</b></p>
            <ul style="color:#c8d6e5;">{_find_html}</ul>
            <p style="margin-bottom:2px;"><b>Suggested actions</b></p>
            <ul style="color:#c8d6e5;">{_act_html}</ul>
            <p style="color:#8fa3b8; font-size:0.85rem;">{_lim_html}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 🤖 Gemini Digital Diagnostic Report")
        if analysis["gemini_status"] == "OK" and analysis["gemini_report"]:
            safe_report = html.escape(analysis["gemini_report"])
            st.markdown(f"""<div class="os-card"><pre style="white-space: pre-wrap; font-family: Rajdhani; color: #c8d6e5;">{safe_report}</pre></div>""", unsafe_allow_html=True)
        elif analysis["gemini_status"] == "NO_KEY":
            st.warning(f"⚠️ {analysis['gemini_error']} The deterministic result above is still valid.")
        elif analysis["gemini_status"] == "ERROR":
            st.error(f"{analysis['gemini_error']} The deterministic result above is still valid.")
        if st.button("📑 CREATE STUDENT TEST REPORT FROM THIS TEST →", key="dig_goto_report_btn", use_container_width=True):
            st.session_state.report_selected_test = analysis.get("test_id")
            st.session_state.page = "Generate Report"
            st.rerun()


# ------------------------------------------------------------------------------
# GENERATE REPORT PAGE (student details, PDF generation, download, e-mail)
# ------------------------------------------------------------------------------
elif st.session_state.page == "Generate Report":
    st.header("📑 GENERATE TEST REPORT")
    st.caption("Create a professional PDF report from a completed NEXUS test, download it, and optionally e-mail it to the student.")

    sd = st.session_state.student_details
    records = list(reversed(st.session_state.analysis_records))

    # ---- 1. choose the exact test record -------------------------------------
    st.markdown("### 🧪 Select Completed Test")
    selected_rec = None
    if not records:
        st.info("No completed test is available yet. Run a test first: **Testing Dashboard → ANALYZE WITH GEMINI** "
                "(rectifier / analogue circuits) or **Digital Circuit Tester → ANALYSE DIGITAL CIRCUIT** (digital circuits). "
                "Then return here to generate the report.")
    else:
        rec_ids = [r["test_id"] for r in records]
        rec_by_id = {r["test_id"]: r for r in records}

        def _rec_label(tid):
            r = rec_by_id[tid]
            res_status = r["result"]["det_status"] if r["kind"] == "digital" else r["result"]["status"]
            return f"{tid} | {r['circuit']} | {r['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} | {res_status}"
        prev_sel = st.session_state.report_selected_test
        sel_index = rec_ids.index(prev_sel) if prev_sel in rec_ids else 0
        chosen_id = st.selectbox("Test record (circuit | date/time | result)", rec_ids, index=sel_index,
                                 format_func=_rec_label, key="rep_test_select")
        st.session_state.report_selected_test = chosen_id
        selected_rec = rec_by_id[chosen_id]
        rr = selected_rec["result"]
        r_status = rr["det_status"] if selected_rec["kind"] == "digital" else rr["status"]
        r_color = "#00ff87" if r_status in ("PASS", "NORMAL") else ("#ff0055" if r_status == "FAIL" else "#ffb703")
        st.markdown(f"""
        <div class="os-card" style="border-left: 5px solid {r_color} !important;">
            <b>{html.escape(selected_rec['circuit'])}</b> ({html.escape(selected_rec['category'])}) &nbsp;|&nbsp;
            Test ID <code>{html.escape(chosen_id)}</code> &nbsp;|&nbsp;
            {selected_rec['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} &nbsp;|&nbsp;
            Result: <b style="color:{r_color};">{html.escape(str(r_status))}</b>
        </div>
        """, unsafe_allow_html=True)
        if selected_rec["kind"] == "digital":
            cur_snapshot = st.session_state.digital_measurements.get(selected_rec["circuit"], {})
            if cur_snapshot != rr.get("measurements_snapshot", {}):
                st.warning("The saved measurements for this circuit have changed since this analysis. The report will use the "
                           "analysed snapshot of this test record. Re-run ANALYSE on the Digital Circuit Tester page to report the newer measurements.")

    # ---- 2. student details -----------------------------------------------------
    st.markdown("### 🎓 Student Details & Report Generation")

    def _mark_attempted():
        st.session_state.report_validate_attempted = True

    def _field_error(field, value_present):
        msg = rep_errors.get(field)
        if msg and (st.session_state.report_validate_attempted or value_present):
            st.markdown(f'<span style="color:#ff4b4b; font-size:0.9rem;">⚠ {html.escape(msg)}</span>', unsafe_allow_html=True)

    f_col1, f_col2 = st.columns(2)
    with f_col1:
        in_name = st.text_input("Student Name *", value=sd.get("name", ""), key="rep_name", max_chars=80)
        name_slot = st.empty()
        year_opts = ["— Select year —"] + REPORT_YEAR_OPTIONS
        year_idx = year_opts.index(sd["year"]) if sd.get("year") in year_opts else 0
        in_year = st.selectbox("Year / Academic Year *", year_opts, index=year_idx, key="rep_year")
        in_year_other = sd.get("year_other", "")
        if in_year.startswith("Other"):
            in_year_other = st.text_input("Type academic year (e.g. 2025-26) *", value=sd.get("year_other", ""), key="rep_year_other", max_chars=40)
        year_slot = st.empty()
    with f_col2:
        in_div = st.text_input("Division *", value=sd.get("division", ""), key="rep_division", max_chars=10, help="For example A, B or C")
        div_slot = st.empty()
        in_email = st.text_input("Email ID *", value=sd.get("email", ""), key="rep_email", max_chars=254, help="The report PDF is e-mailed to this address.")
        email_slot = st.empty()
    with st.expander("Optional details (roll number, college, branch, report title)"):
        o1, o2 = st.columns(2)
        with o1:
            in_roll = st.text_input("Roll number", value=sd.get("roll_no", ""), key="rep_roll", max_chars=40)
            in_branch = st.text_input("Branch", value=sd.get("branch", ""), key="rep_branch", max_chars=80)
        with o2:
            in_college = st.text_input("College name", value=sd.get("college", ""), key="rep_college", max_chars=120)
            in_title = st.text_input("Report title", value=sd.get("report_title", ""), key="rep_title", max_chars=120)

    # keep the entered details across reruns / page changes
    sd.update({"name": in_name, "year": in_year, "year_other": in_year_other, "division": in_div, "email": in_email,
               "roll_no": in_roll, "college": in_college, "branch": in_branch, "report_title": in_title})
    rep_clean, rep_errors = validate_student_details(sd)

    with name_slot.container():
        _field_error("name", bool(in_name.strip()))
    with year_slot.container():
        _field_error("year", bool(in_year_other.strip()) if in_year.startswith("Other") else False)
    with div_slot.container():
        _field_error("division", bool(in_div.strip()))
    with email_slot.container():
        _field_error("email", bool(in_email.strip()))

    # ---- 3. generate -------------------------------------------------------------
    gen_clicked = st.button("📄 Generate PDF Report", key="rep_gen_btn", use_container_width=True,
                            disabled=(selected_rec is None), on_click=_mark_attempted)
    if gen_clicked:
        if rep_errors:
            st.error("Please correct the highlighted student details before generating the report.")
        elif selected_rec is None:
            st.error("No completed test is selected.")
        else:
            try:
                gen_at = datetime.datetime.now()
                with st.spinner("Generating PDF report..."):
                    report_data = build_report_data(selected_rec, rep_clean, gen_at)
                    pdf_bytes = generate_test_report_pdf(report_data)
                if not pdf_bytes or not pdf_bytes.startswith(b"%PDF"):
                    raise ValueError("The PDF generator returned no valid PDF data.")
                st.session_state.report_state = {
                    "pdf_bytes": pdf_bytes,
                    "filename": build_report_filename(rep_clean["name"], selected_rec["circuit"], gen_at),
                    "revision_key": report_revision_key(rep_clean, selected_rec),
                    "test_id": selected_rec["test_id"], "circuit": selected_rec["circuit"],
                    "student": dict(rep_clean), "generated_at": gen_at, "data": report_data,
                    "email_status": None,
                }
            except Exception as exc:
                st.session_state.report_state = None
                st.error(f"PDF generation failed: {exc}")

    # ---- 4. status, download, e-mail ---------------------------------------------
    rs = st.session_state.report_state
    if rs is not None:
        cur_key = report_revision_key(rep_clean, selected_rec) if (selected_rec is not None and not rep_errors) else None
        if rs["revision_key"] != cur_key:
            st.warning(f"A report was generated earlier for **{html.escape(rs['circuit'])}** (Test ID {rs['test_id']}), but the student details or "
                       f"selected test have changed since. Press **Generate PDF Report** again to download or e-mail an up-to-date report.")
        else:
            rd = rs["data"]
            st.success(f"PDF report generated at {rs['generated_at'].strftime('%H:%M:%S')} - ready to download.")
            st.markdown(f"""
            <div class="os-card" style="border-left: 5px solid #00f2fe !important;">
                <b>REPORT SUMMARY</b><br>
                <b>File:</b> {html.escape(rs['filename'])} ({len(rs['pdf_bytes']) / 1024:.1f} KB)<br>
                <b>Student:</b> {html.escape(rs['student']['name'])} | {html.escape(rs['student']['year'])} | Division {html.escape(rs['student']['division'])}<br>
                <b>Circuit:</b> {html.escape(rs['circuit'])} | <b>Test ID:</b> {html.escape(rs['test_id'])}<br>
                <b>Gemini section:</b> {html.escape(rd['gemini']['status'])} &nbsp;|&nbsp;
                <b>Contents:</b> cover &amp; student details, {'logic diagram, truth tables, cell-by-cell comparison, offline diagnosis' if rd['kind'] == 'digital' else 'expected vs measured parameters, calculations, diagnosis'}, recommendations, conclusion
            </div>
            """, unsafe_allow_html=True)
            for line in report_summary_lines(rd):
                st.markdown(f"- {line}")

            st.download_button("⬇️ Download Test Report", data=rs["pdf_bytes"], file_name=rs["filename"],
                               mime="application/pdf", key="rep_download_btn", use_container_width=True)

            st.markdown("#### ✉️ Email Delivery")
            smtp_cfg = load_smtp_settings()
            smtp_problems = smtp_config_problems(smtp_cfg)
            if smtp_problems:
                st.info("Email delivery is not configured (missing/invalid: " + ", ".join(smtp_problems) + "). "
                        "The PDF can still be downloaded above. To enable e-mail, set these environment variables or Streamlit secrets "
                        "(`.streamlit/secrets.toml`): `SMTP_HOST`, `SMTP_PORT` (587 for STARTTLS, 465 for SSL), `SMTP_USERNAME`, "
                        "`SMTP_PASSWORD`, `SMTP_SENDER_EMAIL`. Optional: `SMTP_SECURITY` = `starttls` or `ssl`.")
            send_clicked = st.button(f"📧 Send Report to Email ({rs['student']['email']})", key="rep_send_btn",
                                     use_container_width=True, disabled=bool(smtp_problems))
            if send_clicked:
                with st.spinner("Contacting the SMTP server..."):
                    try:
                        mail_msg = build_report_email(smtp_cfg["sender"], rs["student"]["email"], rs["data"], rs["pdf_bytes"], rs["filename"])
                        ok, msg_txt = send_report_email(smtp_cfg, mail_msg)
                    except Exception as exc:
                        ok, msg_txt = False, f"Email failed: could not prepare the message ({type(exc).__name__})."
                rs["email_status"] = {"ok": ok, "message": msg_txt, "at": datetime.datetime.now(), "to": rs["student"]["email"]}
            es = rs.get("email_status")
            if es:
                stamp = es["at"].strftime("%H:%M:%S")
                if es["ok"]:
                    st.success(f"[{stamp}] {es['message']}")
                else:
                    st.error(f"[{stamp}] {es['message']} The PDF is still available for download above.")
            else:
                st.caption("Email status: not sent yet.")

# ------------------------------------------------------------------------------
# STEP 7: HISTORY PAGE
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

                pdf_bytes = generate_history_pdf(record)
                pdf_file_name = f"NEXUS_Report_{record.get('Date', 'NA')}_{str(record.get('Time', 'NA')).replace(':', '-')}.pdf"
                st.download_button(
                    label="📄 CREATE PDF",
                    data=pdf_bytes,
                    file_name=pdf_file_name,
                    mime="application/pdf",
                    key=f"pdf_{actual_index}"
                )

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
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="about-card">
        <h2 class="about-heading">⚡ AI-Based Electronic & Digital Circuit Tester</h2>
        <p style="font-size: 1.1rem; line-height: 1.6; color: #c8d6e5; margin-top: 10px;">
            An intelligent AI-powered electronic and digital circuit diagnostic platform developed as a <b>Final Year B.Tech Project</b>. 
            The system combines <b>ESP32 hardware</b>, <b>MQTT communication</b>, <b>Streamlit dashboard</b>, and <b>Google Gemini AI</b> 
            to analyze both power rectifiers and digital logic circuits in real time.
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
