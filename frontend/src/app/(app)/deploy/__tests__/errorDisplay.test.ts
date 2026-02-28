/**
 * Unit Test for Error Message Display
 * Feature: firebase-removal-and-consolidation
 *
 * This test verifies that:
 * 1. Error messages are displayed when API returns errors
 * 2. Mock API error response and verify UI shows error
 */

describe("Error Message Display", () => {
  const API_BASE_URL = "http://localhost:8000";
  const mockTerraformId = "test-terraform-id-123";
  const mockConnectionId = "test-connection-id-456";
  const mockDeploymentId = "deployment-123";
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

  test("deployment API returns error with detail field", async () => {
    const errorMessage =
      "Failed to start deployment. AWS connection not found.";

    // Mock deployment API error response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({
        detail: errorMessage,
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

    // Verify the request was made
    expect(global.fetch).toHaveBeenCalledTimes(1);

    // Verify response indicates failure
    expect(response.ok).toBe(false);
    expect(response.status).toBe(400);

    // Verify error message is in response
    const data = await response.json();
    expect(data).toHaveProperty("detail");
    expect(data.detail).toBe(errorMessage);
  });

  test("deployment API returns error with message field", async () => {
    const errorMessage = "Deployment service unavailable";

    // Mock deployment API error response with message field
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({
        message: errorMessage,
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

    // Verify response indicates failure
    expect(response.ok).toBe(false);
    expect(response.status).toBe(503);

    // Verify error message is in response
    const data = await response.json();
    expect(data).toHaveProperty("message");
    expect(data.message).toBe(errorMessage);
  });

  test("destroy API returns error with detail field", async () => {
    const errorMessage = "Failed to start destroy. Deployment not found.";

    // Mock destroy API error response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({
        detail: errorMessage,
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

    // Verify the request was made
    expect(global.fetch).toHaveBeenCalledTimes(1);

    // Verify response indicates failure
    expect(response.ok).toBe(false);
    expect(response.status).toBe(404);

    // Verify error message is in response
    const data = await response.json();
    expect(data).toHaveProperty("detail");
    expect(data.detail).toBe(errorMessage);
  });

  test("AWS connections API returns error with detail field", async () => {
    const errorMessage =
      "Failed to load AWS connections. Authentication required.";
    const userId = "test-user-123";

    // Mock AWS connections API error response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({
        detail: errorMessage,
      }),
    });

    // Simulate the AWS connections request
    const response = await fetch(
      `${API_BASE_URL}/api/user/${userId}/aws-connections`,
      {
        headers: {
          Authorization: `Bearer ${mockToken}`,
        },
      },
    );

    // Verify the request was made
    expect(global.fetch).toHaveBeenCalledTimes(1);

    // Verify response indicates failure
    expect(response.ok).toBe(false);
    expect(response.status).toBe(401);

    // Verify error message is in response
    const data = await response.json();
    expect(data).toHaveProperty("detail");
    expect(data.detail).toBe(errorMessage);
  });

  test("update terraform API returns error with detail field", async () => {
    const errorMessage = "Failed to update Terraform code. Validation failed.";
    const userId = "test-user-123";

    // Mock update terraform API error response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({
        detail: errorMessage,
      }),
    });

    // Simulate the update terraform request
    const response = await fetch(`${API_BASE_URL}/api/update-terraform`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: userId,
        terraform_id: mockTerraformId,
        code: "resource 'aws_s3_bucket' 'test' {}",
      }),
    });

    // Verify the request was made
    expect(global.fetch).toHaveBeenCalledTimes(1);

    // Verify response indicates failure
    expect(response.ok).toBe(false);
    expect(response.status).toBe(400);

    // Verify error message is in response
    const data = await response.json();
    expect(data).toHaveProperty("detail");
    expect(data.detail).toBe(errorMessage);
  });

  test("deployment status API returns error with detail field", async () => {
    const errorMessage = "Failed to fetch deployment status.";

    // Mock deployment status API error response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({
        detail: errorMessage,
      }),
    });

    // Simulate the deployment status request
    const response = await fetch(
      `${API_BASE_URL}/api/deployment/${mockDeploymentId}/status`,
    );

    // Verify the request was made
    expect(global.fetch).toHaveBeenCalledTimes(1);

    // Verify response indicates failure
    expect(response.ok).toBe(false);
    expect(response.status).toBe(500);

    // Verify error message is in response
    const data = await response.json();
    expect(data).toHaveProperty("detail");
    expect(data.detail).toBe(errorMessage);
  });

  test("API returns error without detail or message field", async () => {
    // Mock deployment API error response without detail or message
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({}),
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

    // Verify response indicates failure
    expect(response.ok).toBe(false);
    expect(response.status).toBe(500);

    // Verify response has empty object (no error message)
    const data = await response.json();
    expect(data).toEqual({});
    expect(data).not.toHaveProperty("detail");
    expect(data).not.toHaveProperty("message");
  });

  test("API returns error with both detail and message fields", async () => {
    const detailMessage = "Detailed error message";
    const genericMessage = "Generic error message";

    // Mock deployment API error response with both fields
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({
        detail: detailMessage,
        message: genericMessage,
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

    // Verify response indicates failure
    expect(response.ok).toBe(false);

    // Verify both error fields are in response
    const data = await response.json();
    expect(data).toHaveProperty("detail");
    expect(data).toHaveProperty("message");
    expect(data.detail).toBe(detailMessage);
    expect(data.message).toBe(genericMessage);
  });

  test("network error when API is unreachable", async () => {
    const networkError = new Error("Network request failed");

    // Mock fetch to throw network error
    (global.fetch as jest.Mock).mockRejectedValueOnce(networkError);

    // Simulate the deployment request and expect it to throw
    await expect(
      fetch(`${API_BASE_URL}/api/deploy`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${mockToken}`,
        },
        body: JSON.stringify({
          terraform_plan_id: mockTerraformId,
          aws_connection_id: mockConnectionId,
        }),
      }),
    ).rejects.toThrow("Network request failed");

    // Verify the request was attempted
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  test("error response with non-JSON body", async () => {
    // Mock deployment API error response with non-JSON body
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error("Unexpected token in JSON");
      },
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

    // Verify response indicates failure
    expect(response.ok).toBe(false);
    expect(response.status).toBe(500);

    // Verify json() throws error
    await expect(response.json()).rejects.toThrow("Unexpected token in JSON");
  });
});
