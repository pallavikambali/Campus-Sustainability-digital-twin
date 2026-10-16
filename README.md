# 🌱 Campus Sustainability Digital Twin

An intelligent campus sustainability platform that creates a **digital twin of campus zones** to monitor energy consumption, water usage, occupancy, and waste. The system detects abnormal conditions, visualizes campus status, and provides actionable recommendations.

---

## 📌 Overview

The Campus Sustainability Digital Twin helps educational institutions monitor and improve the use of campus resources through a centralized digital platform.

The system combines:

- 📡 Simulated IoT sensor data
- ⚡ Rule-based anomaly detection
- 💧 Water consumption and leakage monitoring
- 👥 Occupancy monitoring
- ♻️ Computer vision-based waste detection
- 🏫 A 2D digital twin dashboard
- 🤖 GenAI-powered explanations and recommendations
- 🗄️ PostgreSQL-based data storage

The project is designed as a **Minimum Viable Product (MVP)** that can later be integrated with physical sensors such as ESP32 and Arduino devices.

---

## 🎯 Problem Statement

Educational campuses consume significant amounts of electricity and water and generate different types of waste. Without continuous monitoring, issues such as excessive energy consumption, water leakage, unusual occupancy, and overflowing waste bins may go unnoticed.

Traditional monitoring approaches often lack a centralized view of campus conditions and provide limited support for identifying problems early.

Our solution addresses this challenge through a digital platform that monitors campus conditions, detects anomalies, visualizes the status of different zones, and provides recommendations to support sustainable resource management.

---

## 💡 Key Features

### 1. 🏫 Digital Twin Dashboard

A 2D digital representation of campus zones that displays their operational status.

The modeled zones include:

- 🏫 Academic Block
- 📚 Library
- 🏠 Hostel Block

Each zone can display a status such as:

- 🟢 **Normal** — Conditions are within expected limits.
- 🟡 **Warning** — An unusual condition requires attention.
- 🔴 **Critical** — A significant issue requires prompt action.

The dashboard provides a centralized view of campus conditions and detected incidents.

### 2. 📡 Sensor Data Simulation

The MVP simulates sensor readings instead of requiring physical IoT hardware.

The simulated readings cover:

- ⚡ Energy consumption
- 💧 Water consumption
- 👥 Occupancy

The system supports scenarios such as:

- Energy consumption spike
- Possible water leakage
- Occupancy surge
- Reset to normal conditions

This approach allows the application to demonstrate sustainability monitoring without requiring physical sensors.

In future versions, simulated readings can be replaced with data collected from real IoT devices.

### 3. 🚨 Rule-Based Anomaly Detection

The system uses predefined rules and thresholds to identify abnormal campus conditions.

Examples include:

- Excessive energy consumption
- Unusual water consumption that may indicate a leak
- Occupancy exceeding the configured zone capacity

Detected anomalies can be represented as incidents with severity levels such as:

- `WARNING`
- `CRITICAL`

The rules provide a deterministic and explainable method for identifying unusual conditions.

**Important:** GenAI does not perform rule-based anomaly detection. The detection logic identifies the issue before the recommendation system explains it.

### 4. ♻️ Computer Vision Waste Detection

The project includes a modular waste-detection architecture designed to support different detection implementations.

The current implementation supports:

- Mock waste detections for MVP demonstrations
- An optional YOLO-based object-detection pipeline
- Configurable waste-detection severity thresholds

The available `yolo11n.pt` weights contain standard pretrained object classes. They are not a custom-trained waste-overflow model.

Therefore, custom classification of bins as normal, empty, or overflowing has not been established by these weights alone.

The architecture can be extended with a custom-trained model to identify bin conditions from images.

Waste-detection severity levels include:

- `NONE`
- `LOW`
- `MEDIUM`
- `HIGH`

The application can use its configured detection logic to determine severity and associate high-severity detections with incidents for the corresponding campus zone.

**Future enhancement:** Integrate and validate a custom-trained waste-bin classification model using appropriately labelled images.

### 5. 🤖 GenAI-Powered Recommendations

The recommendation component helps explain incidents after they have been detected.

Based on the incident information provided to it, GenAI can assist with:

- Explaining the detected issue
- Describing its possible impact
- Suggesting recommended actions
- Providing sustainability guidance

The application also includes a rule-based fallback mechanism so that recommendations can remain available when the AI service is unavailable, provided the fallback is correctly configured.

**Important:** GenAI is used for explanations and recommendations, not as the primary anomaly-detection mechanism.

### 6. 🗄️ PostgreSQL Database

The backend is designed to use PostgreSQL for persistent application data.

The data model supports information associated with:

- Campus zones
- Sensor readings
- Incidents
- Waste detections
- Recommendations
- Reports

Database storage allows the application to maintain structured sustainability data and support future analytics.

---

## 🏗️ System Architecture

The application follows a modular architecture that separates data simulation, detection, visualization, and recommendations.

```text
                 SENSOR SIMULATOR
                        |
                        v
                 FASTAPI BACKEND
                        |
                        v
                RULE-BASED ANOMALY
                    DETECTION
                        |
                        v
                     INCIDENTS
                        |
             +----------+----------+
             |                     |
             v                     v
      DIGITAL TWIN          GENAI / RULE-BASED
       DASHBOARD              RECOMMENDATIONS


                  WASTE IMAGES
                        |
                        v
                 COMPUTER VISION
                  WASTE DETECTION
                        |
                        v
                WASTE SEVERITY
                        |
                        v
                     INCIDENTS


                  POSTGRESQL
             Persistent Application Data