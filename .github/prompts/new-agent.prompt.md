---
description: "Scaffold a new InfraAgent agent: system prompt, adapter implementation, port interface, and pipeline wiring."
---

# New Agent Scaffold

Create a new agent for the InfraAgent pipeline.

## Agent Details

- **Agent name**: {{agentName}}
- **Purpose**: {{purpose}}
- **Input**: {{input}}
- **Output**: {{output}}

## Steps

1. Create the system prompt at `backend/src/agents/prompts/{{agentName}}.md` following the pattern in existing prompts (role declaration, output schema, quality rules)

2. If this agent has a new responsibility not covered by existing ports, add a new port interface to `backend/src/core/ports.py`:
   ```python
   class INewPort(ABC):
       @abstractmethod
       async def method_name(self, ...) -> ...:
           ...
   ```

3. Create the agent adapter at `backend/src/agents/{{agentName}}.py` implementing the port interface. Follow the pattern in `codegen.py`:
   - Accept `AIProjectClient` and `Agent` in constructor
   - Create thread, send JSON input, poll run, parse JSON response

4. Wire into `backend/src/services/pipeline.py`:
   - Add to `OrchestratorPipeline.__init__()` parameters
   - Call at the appropriate pipeline stage
   - Update `PipelineStage` enum in `core/models.py` if needed

5. Wire into `backend/src/api/routes.py`:
   - Create the agent via `create_agent(client, "{{agentName}}")`
   - Pass to the pipeline constructor

6. Verify the agent name matches the prompt filename: `create_agent(client, "{{agentName}}")` loads `prompts/{{agentName}}.md`
