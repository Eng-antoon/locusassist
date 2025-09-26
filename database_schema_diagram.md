# LocusAssist Database Schema Visualization

## Entity Relationship Diagram

```mermaid
erDiagram
    ORDERS {
        varchar id PK "Primary Key"
        varchar client_id "Client Identifier"
        date date "Order Date"
        varchar order_status "Status (COMPLETED/CANCELLED/ONGOING)"
        varchar location_name "Delivery Location Name"
        text location_address "Full Address"
        varchar location_city "City"
        varchar location_country_code "Country Code"
        float location_latitude "Latitude Coordinate"
        float location_longitude "Longitude Coordinate"
        varchar tour_id "Associated Tour ID"
        varchar tour_date "Tour Date"
        varchar tour_plan_id "Tour Plan ID"
        varchar tour_name "Tour Name"
        int tour_number "Tour Number"
        varchar rider_name "Rider Name"
        varchar rider_id "Rider ID"
        varchar rider_phone "Rider Phone"
        varchar vehicle_registration "Vehicle Registration"
        varchar vehicle_id "Vehicle ID"
        varchar vehicle_model "Vehicle Model"
        varchar transporter_name "Transporter Name"
        timestamp completed_on "Completion Time"
        varchar task_source "Task Source"
        varchar plan_id "Planning ID"
        varchar planned_tour_name "Planned Tour Name"
        int sequence_in_batch "Order Sequence"
        boolean partially_delivered "Partial Delivery Flag"
        boolean reassigned "Reassignment Flag"
        boolean rejected "Rejection Flag"
        boolean unassigned "Unassigned Flag"
        varchar cancellation_reason "Cancellation Reason"
        float tardiness "Delivery Delay"
        varchar sla_status "SLA Status"
        float amount_collected "Amount Collected"
        int effective_tat "Turn-around Time"
        int allowed_dwell_time "Allowed Dwell Time"
        timestamp eta_updated_on "ETA Update Time"
        timestamp tour_updated_on "Tour Update Time"
        timestamp initial_assignment_at "Initial Assignment Time"
        varchar initial_assignment_by "Initial Assigner"
        varchar task_time_slot "Time Slot"
        text skills "Required Skills (JSON)"
        text tags "Tags (JSON)"
        text custom_fields "Custom Fields (JSON)"
        text raw_data "Raw API Data (JSON)"
        boolean is_modified "Manual Modification Flag"
        text modified_fields "Modified Fields (JSON)"
        text cancellation_images "Cancellation Images (JSON)"
        text proof_of_delivery_images "Delivery Proof Images (JSON)"
        varchar last_modified_by "Last Modifier"
        timestamp last_modified_at "Last Modification Time"
        timestamp created_at "Creation Time"
        timestamp updated_at "Last Update Time"
    }

    ORDER_LINE_ITEMS {
        int id PK "Primary Key"
        varchar order_id FK "Foreign Key to Orders"
        varchar sku_id "Product SKU"
        varchar name "Product Name"
        int quantity "Quantity"
        varchar quantity_unit "Unit of Measurement"
        int transacted_quantity "Transacted Quantity"
        varchar transaction_status "Transaction Status"
        boolean is_modified "Manual Modification Flag"
        varchar last_modified_by "Last Modifier"
        timestamp last_modified_at "Last Modification Time"
        timestamp created_at "Creation Time"
    }

    TOURS {
        int id PK "Primary Key"
        varchar tour_id UK "Unique Tour ID"
        varchar tour_date "Tour Date"
        varchar tour_plan_id "Tour Plan ID"
        varchar tour_name "Tour Name"
        int tour_number "Tour Number"
        varchar rider_name "Rider Name"
        varchar rider_id "Rider ID"
        varchar rider_phone "Rider Phone"
        varchar vehicle_registration "Vehicle Registration"
        varchar vehicle_id "Vehicle ID"
        timestamp tour_start_time "Tour Start Time"
        timestamp tour_end_time "Tour End Time"
        int total_orders "Total Orders Count"
        int completed_orders "Completed Orders Count"
        int cancelled_orders "Cancelled Orders Count"
        int pending_orders "Pending Orders Count"
        varchar tour_status "Tour Status (WAITING/ONGOING/CANCELLED/COMPLETED)"
        varchar cancellation_reason "Cancellation Reason"
        text delivery_cities "Delivery Cities (JSON)"
        text delivery_areas "Delivery Areas (JSON)"
        boolean is_modified "Manual Modification Flag"
        text modified_fields "Modified Fields (JSON)"
        varchar last_modified_by "Last Modifier"
        timestamp last_modified_at "Last Modification Time"
        timestamp created_at "Creation Time"
        timestamp updated_at "Last Update Time"
    }

    VALIDATION_RESULTS {
        int id PK "Primary Key"
        varchar order_id "Order ID (No FK Constraint)"
        timestamp validation_date "Validation Date"
        text grn_image_url "GRN Image URL"
        boolean is_valid "Validation Result"
        boolean has_document "Document Detected"
        float confidence_score "AI Confidence Score"
        text extracted_items "Extracted Items (JSON)"
        text discrepancies "Discrepancies (JSON)"
        text summary "Summary (JSON)"
        text gtin_verification "GTIN Verification (JSON)"
        text ai_response "Raw AI Response"
        boolean is_reprocessed "Reprocessing Flag"
        float processing_time "Processing Time (seconds)"
        timestamp created_at "Creation Time"
    }

    DASHBOARD_STATS {
        int id PK "Primary Key"
        date date UK "Date (Unique)"
        int total_orders "Total Orders Count"
        int completed_orders "Completed Orders Count"
        int pending_orders "Pending Orders Count"
        int validated_orders "Validated Orders Count"
        int valid_grns "Valid GRNs Count"
        int invalid_grns "Invalid GRNs Count"
        int grns_with_issues "GRNs with Issues Count"
        int total_gtins_verified "Total GTINs Verified"
        int gtins_matched "GTINs Matched Count"
        int documents_detected "Documents Detected Count"
        int no_documents_detected "No Documents Detected Count"
        float avg_confidence_score "Average Confidence Score"
        float avg_processing_time "Average Processing Time"
        timestamp last_updated "Last Update Time"
    }

    %% Relationships
    ORDERS ||--o{ ORDER_LINE_ITEMS : "has"
    ORDERS ||--o| TOURS : "belongs to"
    ORDERS ||--o| VALIDATION_RESULTS : "validated by"
    ORDERS ||--o{ DASHBOARD_STATS : "aggregated in"
```

## Data Flow Diagram

```mermaid
flowchart TD
    A[Locus API] --> B[Orders Table]
    A --> C[Tours Table]
    
    B --> D[Order Line Items Table]
    B --> E[Validation Results Table]
    B --> F[Dashboard Stats Table]
    
    C --> G[Tour Management]
    D --> H[Item Tracking]
    E --> I[AI Validation]
    F --> J[Dashboard Analytics]
    
    K[Manual Editing] --> B
    K --> C
    K --> D
    
    L[User Interface] --> M[Order Management]
    L --> N[Tour Management]
    L --> O[Validation System]
    L --> P[Dashboard]
    
    M --> B
    N --> C
    O --> E
    P --> F
    
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#e8f5e8
    style D fill:#fff3e0
    style E fill:#fce4ec
    style F fill:#f1f8e9
```

## Table Statistics

| Table | Records | Key Relationships | Purpose |
|-------|---------|-------------------|---------|
| **orders** | 1,472 | Central hub table | Main order management |
| **order_line_items** | 5,902 | FK to orders | Item-level tracking |
| **tours** | 409 | Logical link to orders | Tour management |
| **validation_results** | 1 | Logical link to orders | AI validation |
| **dashboard_stats** | 0 | Aggregated from others | Analytics |

## Key Relationships

### 1. **Primary Foreign Key**
- `order_line_items.order_id` → `orders.id` (One-to-Many)

### 2. **Logical Relationships** (No FK constraints)
- `orders.tour_id` ↔ `tours.tour_id` (Many-to-One)
- `validation_results.order_id` ↔ `orders.id` (One-to-One)

### 3. **Data Flow**
1. **Orders** are created from Locus API
2. **Order Line Items** are linked to orders
3. **Tours** are associated with orders via `tour_id`
4. **Validation Results** are created for orders
5. **Dashboard Stats** are aggregated from all tables

## Status Distributions

### Order Status
- **COMPLETED**: 1,302 (88.5%)
- **CANCELLED**: 147 (10.0%)
- **ONGOING**: 23 (1.6%)

### Tour Status
- **COMPLETED**: 402 (98.3%)
- **ONGOING**: 6 (1.5%)
- **CANCELLED**: 1 (0.2%)

## Features

### Editing Support
- All main tables have `is_modified` flags
- Track `last_modified_by` and `last_modified_at`
- Store `modified_fields` as JSON

### Location Data
- Full address information
- Latitude/longitude coordinates
- City and country codes

### Performance Tracking
- SLA status and tardiness
- Turn-around times
- Amount collection tracking

### AI Integration
- Validation results with confidence scores
- Document detection
- GTIN verification
- Processing time tracking
