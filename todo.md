# Project Checklist: GitLab LLM Code Review Bot

## Phase 1: Project Initialization & Configuration Loader
- [ ] Initialize project directory structure (`src/`, `tests/`, `terraform/`).
- [ ] Create `requirements.txt` with essential dependencies:
  - `pytest`
  - `pytest-mock`
  - `pyyaml`
  - `requests`
  - `requests-mock`
- [ ] Create empty initialization file `src/__init__.py`.
- [ ] Create `src/config.yaml` containing provider, model, and base system prompt schemas.
- [ ] Implement `src/config_loader.py` to parse the YAML file safely.
  - [ ] Add explicit validation logic to ensure required configuration keys are present.
  - [ ] Add clean exception raising if the file is missing or corrupted.
- [ ] Implement `tests/test_config.py`:
  - [ ] Test successful parsing of a valid configuration file.
  - [ ] Test that missing or malformed YAML configurations throw the expected custom exceptions.

---

## Phase 2: Webhook Security & Event Ingress Guarding
- [ ] Create skeleton `src/handler.py` containing the baseline `lambda_handler(event, context)` wrapper.
- [ ] Implement request header checking to locate and extract the `X-Gitlab-Token`.
- [ ] Implement constant-time string comparison using `hmac.compare_digest`.
  - [ ] Pull target string securely from the `GITLAB_WEBHOOK_SECRET` environment variable.
  - [ ] Return an HTTP 401 Unauthorized structure dictionary for invalid/missing tokens.
- [ ] Create `tests/test_handler_security.py`:
  - [ ] Verify valid tokens successfully bypass the security block.
  - [ ] Verify invalid or completely missing tokens explicitly return an HTTP 401 state.
- [ ] Implement JSON request body parsing inside `src/handler.py` with protective `try/except` catchments.
- [ ] Implement event payload filtering criteria:
  - [ ] Validate `object_kind` equals exactly `"note"`.
  - [ ] Verify the existence of the `merge_request` block key.
  - [ ] Inspect `object_attributes.note` for the exact string sequence `/review`.
- [ ] Return a graceful HTTP 200 OK "Event ignored" no-op response for all filtered-out events.
- [ ] Create `tests/test_handler_filter.py`:
  - [ ] Test matching payloads containing `/review` proceed correctly.
  - [ ] Test unrelated comments, system updates, or non-MR notes trigger a clean 200 OK short-circuit.

---

## Phase 3: GitLab Context Gathering Engine
- [ ] Create `src/gitlab_client.py` and implement the `GitLabClient` class.
  - [ ] Add initialization logic mapping a base URL and a secret `GITLAB_TOKEN`.
- [ ] Implement `get_merge_request_diffs(project_id, merge_request_iid)` targeting `/projects/:id/merge_requests/:mr_iid/changes`.
  - [ ] Build custom exception class `GitLabAPIError` to catch non-200 responses.
- [ ] Create `tests/test_gitlab_client.py` to verify API token propagation and response dictionary parsing.
- [ ] Create `src/file_filter.py` and implement the `should_review_file(file_path)` selector.
  - [ ] Define exclusion regex for lockfiles (`package-lock.json`, `yarn.lock`, etc.).
  - [ ] Define exclusion regex for minified assets (`*.min.js`, `*.min.css`).
  - [ ] Define exclusion regex for media/binary types (`.png`, `.jpg`, `.pdf`, `.zip`).
- [ ] Create `tests/test_file_filter.py` using `pytest` parameterization to thoroughly validate multiple file targets.
- [ ] Implement `get_raw_file_content(project_id, file_path, ref)` inside `src/gitlab_client.py`.
  - [ ] Integrate explicit URL-encoding safeguards for the `file_path` segment.
  - [ ] Handle 404 missing file states gracefully.
- [ ] Update `tests/test_gitlab_client.py` to assert the integrity of raw file retrievals.

---

## Phase 4: Modular LLM Layer & JSON Schema Enforcement
- [ ] Define `BaseLLMProvider` abstract base class within `src/llm_factory.py`.
- [ ] Build out concrete `GeminiProvider(BaseLLMProvider)` calling model endpoints directly via `requests`.
- [ ] Implement `LLMFactory` class to handle dynamic runtime provider selection.
- [ ] Create `tests/test_llm_factory.py` ensuring configuration targets resolve to correct concrete object instances.
- [ ] Update prompt compilation logic to explicitly mandate and append a strict output schema structure:
  - [ ] Array of objects containing `file_path`, `line_number`, and `comment`.
- [ ] Build robust JSON extraction utility handling edge-case markdown formatting:
  - [ ] Clean and strip markdown code wrapper boundaries (` ```json ... ``` `).
  - [ ] Throw custom exception `MalformedLLMResponse` for corrupted JSON architectures.
- [ ] Create `tests/test_llm_parser.py` validating pristine structural outputs, raw markdown text extractions, and corrupted payloads.

---

## Phase 5: Feedback Delivery & Resiliency Control
- [ ] Implement `post_merge_request_comment(project_id, merge_request_iid, body)` inside `src/gitlab_client.py`.
- [ ] Implement target line `post_inline_discussion(project_id, merge_request_iid, file_path, line_number, comment_text)`.
- [ ] Update client tests to verify both global comments and inline thread configurations.
- [ ] Build an interactive line-mapping loop mapping LLM array output downstream to GitLab:
  - [ ] Trap 400 Bad Request responses (representing line/file target hallucinations).
  - [ ] Fail-soft gracefully by rerouting the corrupted comment block to the global MR Overview tab.
- [ ] Implement global system catchments around the orchestration loop:
  - [ ] Log complete tracebacks to stdout/CloudWatch for debugging.
  - [ ] Post a clean fallback notification text to the developer: `"⚠️ Sorry, I encountered an error while processing this review."`
- [ ] Create `tests/test_error_handling.py` verifying line posting routing fallback loops and full infrastructure exception isolation.

---

## Phase 6: Orchestration Wiring & Integration
- [ ] Complete orchestration sequences directly inside `lambda_handler` (`src/handler.py`):
  - [ ] Trigger security guard handshakes.
  - [ ] Evaluate payload filter specifications.
  - [ ] Immediate posting of tracking acknowledgment comment (`⏳ Review in progress...`).
  - [ ] Compile file lists, apply filters, and pull raw code contents.
  - [ ] Invoke the dynamic LLM provider.
  - [ ] Execute the inline review delivery sequence with active line-fallbacks.
- [ ] Create a comprehensive end-to-end integration test wrapper `tests/test_integration.py`:
  - [ ] Mock the entire external API ecosystem (GitLab and LLM endpoints).
  - [ ] Feed mock event payloads completely through `lambda_handler` and assert successful HTTP 200 outputs.

---

## Phase 7: Infrastructure as Code (Terraform Deployment)
- [ ] Create `terraform/variables.tf` parameterizing region, tagging structures, and secret parameters.
- [ ] Create `terraform/outputs.tf` tracking and exporting the deployment API Gateway endpoint address.
- [ ] Implement `terraform/main.tf` configuring:
  - [ ] AWS Secrets Manager container allocation for secure variable tracking.
  - [ ] IAM Execution Roles providing restrictive execution boundaries (CloudWatch Logs + Secrets access).
  - [ ] CloudWatch Log Group tracking with strict 14-day archival retention rules.
  - [ ] AWS Lambda Function deployments sourcing compiled archive paths (`../src`).
  - [ ] AWS API Gateway resource blocks routing execution streams into our target Lambda instance.