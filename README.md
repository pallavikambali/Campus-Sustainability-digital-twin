# Campus Sustainability Digital Twin 🌱

A smart campus sustainability platform that creates a **digital twin of campus zones** to monitor energy, water, occupancy, and waste, detect abnormal conditions, and provide intelligent recommendations.

## 📌 Overview

The Campus Sustainability Digital Twin is designed to help educational institutions monitor and improve the use of campus resources.

The system combines:

- Simulated IoT sensor data
- Rule-based anomaly detection
- Computer Vision for waste detection
- A real-time 2D digital twin dashboard
- GenAI-powered explanations and recommendations
- PostgreSQL-based data storage

The project is designed as an MVP that can later be connected to real sensors such as ESP32/Arduino devices.

---

## 🎯 Problem Statement

Educational campuses consume significant amounts of electricity and water and generate different types of waste. Without continuous monitoring, problems such as:

- Excessive energy consumption
- Water leakage
- Abnormal occupancy
- Improper waste disposal

may go unnoticed.

Our solution provides a centralized digital platform to monitor campus conditions, detect anomalies, visualize them on a digital twin, and provide actionable recommendations.

---

## 💡 Key Features

### 1. Digital Twin Dashboard

A 2D digital representation of campus zones that displays their current operational status.

Currently modeled zones include:

- 🏫 Academic Block
- 📚 Library
- 🏠 Hostel Block

Each zone can have a status such as:

- 🟢 Normal
- 🟡 Warning
- 🔴 Critical

---

### 2. Sensor Data Simulation

Since physical IoT sensors are not required for the MVP, the system currently simulates sensor readings for:

- ⚡ Energy consumption
- 💧 Water consumption
- 👥 Occupancy

The simulator can generate different scenarios such as:

- Energy spike
- Water leakage
- Occupancy surge
- Reset to normal conditions

This architecture allows simulated sensors to be replaced with real IoT devices later.

---

### 3. Rule-Based Anomaly Detection

The system uses deterministic rules to identify abnormal conditions.

Examples:

- Excessive energy consumption
- Possible water leakage
- Occupancy exceeding the zone capacity

Detected anomalies are converted into incidents with severity levels such as:

- WARNING
- CRITICAL

> **Important:** GenAI is not responsible for detecting anomalies. Detection is performed using predefined rules and Computer Vision.

---

### 4. Computer Vision Waste Detection

The project includes a replaceable waste detection architecture.

Currently, a mock detector is used for the MVP, while the system is designed to support an optional YOLO-based detector.

The system can classify waste detection severity based on the number of detected waste objects.

Severity levels include:

- NONE
- LOW
- MEDIUM
- HIGH

A high-severity waste detection can generate an active incident for the corresponding zone.

---

### 5. GenAI Recommendations 🤖

GenAI is used after an incident has already been detected.

It receives trusted incident information and provides:

- Explanation of the detected issue
- Possible impact
- Recommended actions
- Advisory guidance

The system also includes a rule-based fallback so that recommendations remain available even when the AI service is unavailable.

> **GenAI does not perform anomaly detection. It explains detected incidents and provides recommendations.**

---

## 🏗️ System Architecture

```text
                    ┌─────────────────────┐
                    │   Sensor Simulator  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      Backend        │
                    │      FastAPI        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Rule-Based        │
                    │ Anomaly Detection   │
                    └──────────┬──────────┘
                               │
              ┌────────────────┴────────────────┐
              ▼                                 ▼
    ┌──────────────────┐              ┌──────────────────┐
    │   Digital Twin   │              │ Computer Vision  │
    │    Dashboard     │              │ Waste Detection  │
    └────────┬─────────┘              └────────┬─────────┘
             │                                 │
             └────────────────┬────────────────┘
                              ▼
                    ┌─────────────────────┐
                    │       GenAI         │
                    │ Recommendations &   │
                    │    Explanations     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     PostgreSQL      │
                    │      Database       │
                    └─────────────────────┘