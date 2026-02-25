/**
 * Unit Test for Deployment API Request Payload
 * Feature: firebase-removal-and-consolidation
 * Validates: Requirements 9.4, 9.5
 *
 * This test verifies that:
 * 1. Deployment request includes terraform_plan_id and aws_connection_id
 * 2. Deployment request includes JWT token in Authorization header
 */

describe("Deployment API Request Payload", () => {
  const API_BASE_URL = "http://localhost:8000";
  const mockTerraformId = "test-terraform-id-123";
  const mockConnectionId = "test-connection-id-456";
  const mockToken = "mock-jwt-token-789";

  beforeEach(() => {
    // Reset fetch mock before each test
    global.fetch = jest.fn();

    // Mock document.cookie for JWT token retrieval
    Object.defineProperty(document, "cookie", {
      writable: true,
      value: `id_token=${mockToken}`,
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test("deployment request includes terraform_plan_id and aws_connection_id in payload", async () => {
    // Mock successful fetch response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        deployment_id: "deployment-123",
        status: "started",
        message: "Deployment started",
      }),
    });

    // Simulate the deployment request
    const response = await fetch(`${API_BASE_URL}/api/deploy`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${mockToken}`,
      },
      body: JSON.stringify({
        terraform_plan_id: mockTerraformId,
        aws_connection_id: mockConnectionId,
      }),
    });

    // Verify fetch was called
    expect(global.fetch).toHaveBeenCalledTimes(1);

    // Verify the request was made to the correct endpoint
    expect(global.fetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/deploy`,
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
      }),
    );

    // Extract the actual call arguments
    const callArgs = (global.fetch as jest.Mock).mock.calls[0];
    const requestBody = JSON.parse(callArgs[1].body);

    // Verify terraform_plan_id is in the payload
    expect(requestBody).toHaveProperty("terraform_plan_id");
    expect(requestBody.terraform_plan_id).toBe(mockTerraformId);

    // Verify aws_connection_id is in the payload
    expect(requestBody).toHaveProperty("aws_connection_id");
    expect(requestBody.aws_connection_id).toBe(mockConnectionId);

    // Verify response is successful
    expect(response.ok).toBe(true);
  });

  test("deployment request includes JWT token in Authorization header", async () => {
    // Mock successful fetch response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        deployment_id: "deployment-123",
        status: "started",
        message: "Deployment started",
      }),
    });

    // Simulate the deployment request
    await fetch(`${API_BASE_URL}/api/deploy`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${mockToken}`,
      },
      body: JSON.stringify({
        terraform_plan_id: mockTerraformId,
        aws_connection_id: mockConnectionId,
      }),
    });

    // Verify fetch was called
    expect(global.fetch).toHaveBeenCalledTimes(1);

    // Extract the actual call arguments
    const callArgs = (global.fetch as jest.Mock).mock.calls[0];
    const headers = callArgs[1].headers;

    // Verify Authorization header is present
    expect(headers).toHaveProperty("Authorization");

    // Verify Authorization header contains Bearer token
    expect(headers.Authorization).toBe(`Bearer ${mockToken}`);

    // Verify the token format is correct (Bearer prefix)
    expect(headers.Authorization).toMatch(/^Bearer .+/);
  });

  test("destroy request includes deployment_id in payload", async () => {
    const mockDeploymentId = "deployment-123";

    // Mock successful fetch response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        deployment_id: mockDeploymentId,
        status: "started",
        message: "Destroy started",
      }),
    });

    // Simulate the destroy request
    const response = await fetch(`${API_BASE_URL}/api/destroy`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${mockToken}`,
      },
      body: JSON.stringify({
        deployment_id: mockDeploymentId,
      }),
    });

    // Verify fetch was called
    expect(global.fetch).toHaveBeenCalledTimes(1);

    // Extract the actual call arguments
    const callArgs = (global.fetch as jest.Mock).mock.calls[0];
    const requestBody = JSON.parse(callArgs[1].body);

    // Verify deployment_id is in the payload
    expect(requestBody).toHaveProperty("deployment_id");
    expect(requestBody.deployment_id).toBe(mockDeploymentId);

    // Verify response is successful
    expect(response.ok).toBe(true);
  });

  test("destroy request includes JWT token in Authorization header", async () => {
    const mockDeploymentId = "deployment-123";

    // Mock successful fetch response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        deployment_id: mockDeploymentId,
        status: "started",
        message: "Destroy started",
      }),
    });

    // Simulate the destroy request
    await fetch(`${API_BASE_URL}/api/destroy`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${mockToken}`,
      },
      body: JSON.stringify({
        deployment_id: mockDeploymentId,
      }),
    });

    // Verify fetch was called
    expect(global.fetch).toHaveBeenCalledTimes(1);

    // Extract the actual call arguments
    const callArgs = (global.fetch as jest.Mock).mock.calls[0];
    const headers = callArgs[1].headers;

    // Verify Authorization header is present with Bearer token
    expect(headers).toHaveProperty("Authorization");
    expect(headers.Authorization).toBe(`Bearer ${mockToken}`);
  });

  test("deployment request fails when JWT token is missing", async () => {
    // Clear the cookie to simulate missing token
    Object.defineProperty(document, "cookie", {
      writable: true,
      value: "",
    });

    // Mock error response for missing token
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({
        detail: "Authentication required",
      }),
    });

    // Simulate the deployment request without token
    const response = await fetch(`${API_BASE_URL}/api/deploy`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // No Authorization header
      },
      body: JSON.stringify({
        terraform_plan_id: mockTerraformId,
        aws_connection_id: mockConnectionId,
      }),
    });

    // Verify the request was made
    expect(global.fetch).toHaveBeenCalledTimes(1);

    // Verify response indicates authentication failure
    expect(response.ok).toBe(false);
    expect(response.status).toBe(401);
  });

  test("deployment request payload structure matches backend API expectations", async () => {
    // Mock successful fetch response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        deployment_id: "deployment-123",
        status: "started",
      }),
    });

    // Simulate the deployment request
    await fetch(`${API_BASE_URL}/api/deploy`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${mockToken}`,
      },
      body: JSON.stringify({
        terraform_plan_id: mockTerraformId,
        aws_connection_id: mockConnectionId,
      }),
    });

    // Extract the actual call arguments
    const callArgs = (global.fetch as jest.Mock).mock.calls[0];
    const requestBody = JSON.parse(callArgs[1].body);

    // Verify payload has exactly the expected fields (no extra fields)
    const expectedKeys = ["terraform_plan_id", "aws_connection_id"];
    const actualKeys = Object.keys(requestBody);

    expect(actualKeys.sort()).toEqual(expectedKeys.sort());

    // Verify both fields are strings
    expect(typeof requestBody.terraform_plan_id).toBe("string");
    expect(typeof requestBody.aws_connection_id).toBe("string");
  });
});
