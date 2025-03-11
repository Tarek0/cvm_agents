# Customer Value Management (CVM) Multi-Agent Architecture

## Overview

The CVM multi-agent architecture divides the treatment selection process into specialized components, each responsible for specific aspects of the workflow. This modular approach improves maintainability, scalability, and allows for independent optimization of each component.

## Agent Architecture

```mermaid
flowchart TD
    client[Client Application] --> orch
    
    subgraph "Multi-Agent System"
        orch[Orchestrator Agent] --> trigger
        orch --> data
        orch --> journey
        orch --> treatment
        orch --> allocation
        
        trigger[Trigger Agent] --> |Identified Customers| data
        data[Data Agent] --> |Raw Customer Data| journey
        journey[Journey Agent] --> |Customer Journey| treatment
        treatment[Treatment Agent] --> |Treatment Recommendation| allocation
        allocation[Allocation Agent] --> |Resource Availability| treatment
    end
    
    trigger -.-> |Analyzes| db[(Data Sources)]
    data -.-> |Fetches Data| db
    treatment -.-> |Uses| llm[LLM Service]
    allocation -.-> |Manages| constraints[(Resource Constraints)]
    
    classDef primary fill:#f9f,stroke:#333,stroke-width:2px;
    classDef secondary fill:#bbf,stroke:#333,stroke-width:1px;
    classDef external fill:#ddd,stroke:#333,stroke-width:1px;
    
    class orch primary;
    class trigger,data,journey,treatment,allocation secondary;
    class db,llm,constraints external;
```

## Agent Responsibilities

### 1. Trigger Agent

The Trigger Agent is responsible for identifying customers who match specific criteria:

- Uses both rule-based and LLM-powered analysis to identify customers that need attention
- Supports predefined trigger types for common scenarios (network issues, billing disputes, etc.)
- Enables custom semantic triggers using natural language descriptions
- Analyzes customer interactions from multiple channels (calls, chat sessions)
- Provides evidence and reasoning for why customers match specific criteria

The Trigger Agent supports operations such as:
- `trigger_customers`: Identifies customers matching specified criteria
- `list_triggers`: Returns available trigger types
- Various specialized trigger functions for common scenarios

### 2. Orchestrator Agent

The Orchestrator Agent is the central coordinator that manages the entire workflow:

- Initializes and coordinates all other agents
- Defines the sequence of operations for processing customers
- Handles error recovery and fallback strategies
- Aggregates results and produces the final output

The orchestrator follows a clear step-by-step process for each customer:
1. Request customer data from the Data Agent
2. Pass the data to the Journey Agent to build a customer journey
3. Retrieve customer permissions 
4. Request treatment recommendations from the Treatment Agent
5. Allocate resources using the Allocation Agent
6. Handle fallback scenarios when primary treatments aren't available

### 3. Data Agent

The Data Agent is responsible for all data access operations:

- Retrieves customer data from various sources (files, databases)
- Implements caching for efficient repeat data access
- Handles data transformation and normalization
- Abstracts away data source complexity from other agents

The Data Agent supports operations such as:
- `get_customer_data`: Retrieves all data for a specific customer
- `clear_cache`: Clears the data cache when needed

### 4. Journey Agent

The Journey Agent builds and analyzes customer journeys:

- Constructs comprehensive customer journey from raw data points
- Identifies patterns and trends in customer behavior
- Extracts key metrics and insights from journeys
- Creates summarized versions of journeys when needed

The Journey Agent supports operations such as:
- `build_journey`: Constructs a journey from raw customer data
- `analyze_journey`: Extracts insights from a journey
- `summarize_journey`: Creates a condensed version of a journey

### 5. Treatment Agent

The Treatment Agent determines the optimal treatment for customers:

- Uses LLMs to analyze customer journeys and determine best treatments
- Applies business rules and customer permissions to recommendations
- Finds alternative treatments when primary choices are unavailable
- Provides explanations for treatment decisions

The Treatment Agent supports operations such as:
- `recommend_treatment`: Recommends optimal treatment based on customer journey
- `find_alternative_treatment`: Finds alternatives when primary treatment is unavailable

### 6. Allocation Agent

The Allocation Agent manages resource allocation and constraints:

- Tracks availability of limited resources (e.g., call center slots)
- Ensures thread-safe updates to resource constraints
- Implements priority-based allocation for high-value customers
- Maintains allocation history for analysis

The Allocation Agent supports operations such as:
- `allocate_resource`: Attempts to allocate a resource for a treatment
- `check_availability`: Checks if a resource is available
- `get_constraints`: Returns current constraint status
- `reset_constraints`: Resets constraints to initial values

## Communication Flow

The agents communicate through a standardized message-passing interface:

1. Each agent implements a `process(message)` method that accepts messages with a `type` field
2. The message type determines which operation the agent will perform
3. Messages include all necessary data for the operation
4. Agents return responses that may be used as inputs to other agents

This approach allows for:
- Loose coupling between agents
- Easy testing of individual agents
- Future extension to distributed messaging systems

## System Workflow

```mermaid
sequenceDiagram
    title Customer Value Management (CVM) Multi-Agent System Workflow
    
    participant Client
    participant Trigger as TriggerAgent
    participant Orchestrator as OrchestratorAgent
    participant Data as DataAgent
    participant Journey as JourneyAgent
    participant Treatment as TreatmentAgent
    participant Allocation as AllocationAgent

    alt Direct Customer Processing
        Client->>Orchestrator: process_customer(customer_id)
    else Triggered Customer Processing
        Client->>Trigger: trigger_customers(customer_ids, trigger_type, custom_trigger)
        Note over Trigger: Analyzes customer interactions<br/>to identify those matching<br/>specific criteria
        Trigger-->>Client: {matches: [matching customers], total_matches}
        
        Client->>Orchestrator: process_batch(matching_customer_ids)
    end
    
    %% Data Collection Phase
    Orchestrator->>Data: process({type: "get_customer_data", customer_id})
    Note over Data: Retrieves and caches<br/>customer data from<br/>various sources
    Data-->>Orchestrator: customer_data
    
    %% Journey Building Phase
    Orchestrator->>Journey: process({type: "build_journey", customer_id, customer_data})
    Note over Journey: Constructs customer journey<br/>from raw data and<br/>identifies patterns
    Journey-->>Orchestrator: {journey: customer_journey}
    
    %% Permissions Retrieval
    Orchestrator->>Orchestrator: _get_customer_permissions(customer_id)
    Note over Orchestrator: Loads customer contact<br/>permissions from<br/>permissions.json
    
    %% Treatment Recommendation Phase
    Orchestrator->>Treatment: process({type: "recommend_treatment", journey, treatments, constraints, permissions})
    Note over Treatment: Uses LLM to analyze<br/>customer journey and<br/>recommend best treatment<br/>based on business rules
    Treatment-->>Orchestrator: {selected_treatment, explanation}
    
    %% Resource Allocation Phase
    alt selected_treatment != "ignore"
        Orchestrator->>Allocation: process({type: "allocate_resource", treatment_key, customer_id})
        Note over Allocation: Thread-safe allocation<br/>of limited resources<br/>based on availability
        
        alt allocation successful
            Allocation-->>Orchestrator: {status: "success", allocated: true}
        else allocation failed
            Allocation-->>Orchestrator: {status: "error", message}
            
            %% Find Alternative Treatment
            Orchestrator->>Treatment: process({type: "find_alternative", journey, excluded_treatment, treatments, constraints, permissions})
            Note over Treatment: Finds alternative treatment<br/>when primary is unavailable
            Treatment-->>Orchestrator: {selected_treatment, explanation}
            
            %% Try Allocating Alternative
            Orchestrator->>Allocation: process({type: "allocate_resource", treatment_key, customer_id})
            Allocation-->>Orchestrator: Response
        end
    end
    
    %% Result Creation
    Orchestrator->>Client: {customer_id, selected_treatment, explanation, status: "success"}
```

## Benefits of the Multi-Agent Architecture

1. **Modularity**: Each agent focuses on a specific aspect of the overall system
2. **Scalability**: Agents can be scaled independently based on workload
3. **Maintainability**: Changes to one agent's implementation don't affect others
4. **Extensibility**: New capabilities can be added as new agent types
5. **Resilience**: Failures in one agent can be contained without crashing the entire system
6. **Optimization**: Each agent can be optimized for its specific task
7. **Reusability**: Agents can be reused across different workflows

## Future Enhancements

The current implementation can be extended with:

1. **Evaluation Agent**: For assessing treatment effectiveness
2. **Learning Agent**: For improving treatments based on historical outcomes
3. **Messaging Infrastructure**: Replace direct method calls with message queues
4. **Distributed Processing**: Distribute agents across multiple servers
5. **A/B Testing Framework**: Test different agent strategies in parallel