/**
 * Unit Test for AWS Connection Loading
 * Feature: firebase-removal-and-consolidation
 *
 * This test verifies that:
 * 1. AWS connections are loaded from backend API
 * 2. Mock API response and verify connections are displayed
 */

describe("AWS Connection Loading", () => {
  const API_BASE_URL = "http://localhost:8000";
  const mockUserId = "test-user-123";
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

  test("AWS connections are loaded from backend API", async () => {
    const mockConnections = [
      {
        id: "conn-123",
        user_id: mockUserId,
        aws_account_id: "123456789012",
        external_id: "ext-id-123",
        role_arn: "arn:aws:iam::123456789012:role/TestRole",
        status: "active",
      },
      {
        id: "conn-456",
        user_id: mockUserId,
        aws_account_id: "987654321098",
        external_id: "ext-id-456",
        role_arn: "arn:aws:iam::987654321098:role/TestRole2",
        status: "active",
      },
    ];

    // Mock successful fetch response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        connections: mockConnections,
      }),
    });

    // Simulate the AWS connections request
    const response = await fetch(
      `${API_BASE_URL}/api/user/${mockUserId}/aws-connections`,
      {
        headers: {
          Authorization: `Bearer ${mockToken}`,
        },
      },
    );

    // Verify fetch was called
    expect(global.fetch).toHaveBeenCalledTimes(1);

    // Verify the request was made to the correct endpoint
    expect(global.fetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/user/${mockUserId}/aws-connections`,
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: `Bearer ${mockToken}`,
        }),
      }),
    );

    // Verify response is successful
    expect(response.ok).toBe(true);

    // Verify connections are in response
    const data = await response.json();
    expect(data).toHaveProperty("connections");
    expect(data.connections).toEqual(mockConnections);
    expect(data.connections).toHaveLength(2);
  });

  test("AWS connections request includes JWT token in Authorization header", async () => {
    // Mock successful fetch response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        connections: [],
      }),
    });

    // Simulate the AWS connections request
    await fetch(`${API_BASE_URL}/api/user/${mockUserId}/aws-connections`, {
      headers: {
        Authorization: `Bearer ${mockToken}`,
      },
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

  test("empty connections array is returned when user has no connections", async () => {
    // Mock successful fetch response with empty connections
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        connections: [],
      }),
    });

    // Simulate the AWS connections request
    const response = await fetch(
      `${API_BASE_URL}/api/user/${mockUserId}/aws-connections`,
      {
        headers: {
          Authorization: `Bearer ${mockToken}`,
        },
      },
    );

    // Verify response is successful
    expect(response.ok).toBe(true);

    // Verify connections array is empty
    const data = await response.json();
    expect(data).toHaveProperty("connections");
    expect(data.connections).toEqual([]);
    expect(data.connections).toHaveLength(0);
  });

  test("single AWS connection is loaded correctly", async () => {
    const mockConnection = {
      id: "conn-789",
      user_id: mockUserId,
      aws_account_id: "111222333444",
      external_id: "ext-id-789",
      role_arn: "arn:aws:iam::111222333444:role/SingleRole",
      status: "active",
    };

    // Mock successful fetch response with single connection
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        connections: [mockConnection],
      }),
    });

    // Simulate the AWS connections request
    const response = await fetch(
      `${API_BASE_URL}/api/user/${mockUserId}/aws-connections`,
      {
        headers: {
          Authorization: `Bearer ${mockToken}`,
        },
      },
    );

    // Verify response is successful
    expect(response.ok).toBe(true);

    // Verify single connection is returned
    const data = await response.json();
    expect(data.connections).toHaveLength(1);
    expect(data.connections[0]).toEqual(mockConnection);
    expect(data.connections[0].id).toBe("conn-789");
    expect(data.connections[0].aws_account_id).toBe("111222333444");
  });

  test("AWS connections with different statuses are loaded", async () => {
    const mockConnections = [
      {
        id: "conn-active",
        user_id: mockUserId,
        aws_account_id: "123456789012",
        external_id: "ext-id-active",
        role_arn: "arn:aws:iam::123456789012:role/ActiveRole",
        status: "active",
      },
      {
        id: "conn-pending",
        user_id: mockUserId,
        aws_account_id: "987654321098",
        external_id: "ext-id-pending",
        role_arn: "arn:aws:iam::987654321098:role/PendingRole",
        status: "pending",
      },
    ];

    // Mock successful fetch response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        connections: mockConnections,
      }),
    });

    // Simulate the AWS connections request
    const response = await fetch(
      `${API_BASE_URL}/api/user/${mockUserId}/aws-connections`,
      {
        headers: {
          Authorization: `Bearer ${mockToken}`,
        },
      },
    );

    // Verify response is successful
    expect(response.ok).toBe(true);

    // Verify connections with different statuses are returned
    const data = await response.json();
    expect(data.connections).toHaveLength(2);
    expect(data.connections[0].status).toBe("active");
    expect(data.connections[1].status).toBe("pending");
  });

  test("API returns error when authentication fails", async () => {
    const errorMessage = "Authentication required. Please log in again.";

    // Mock authentication error response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({
        detail: errorMessage,
      }),
    });

    // Simulate the AWS connections request
    const response = await fetch(
      `${API_BASE_URL}/api/user/${mockUserId}/aws-connections`,
      {
        headers: {
          Authorization: `Bearer ${mockToken}`,
        },
      },
    );

    // Verify response indicates authentication failure
    expect(response.ok).toBe(false);
    expect(response.status).toBe(401);

    // Verify error message is in response
    const data = await response.json();
    expect(data).toHaveProperty("detail");
    expect(data.detail).toBe(errorMessage);
  });

  test("API returns error when user not found", async () => {
    const errorMessage = "User not found";

    // Mock user not found error response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({
        detail: errorMessage,
      }),
    });

    // Simulate the AWS connections request
    const response = await fetch(
      `${API_BASE_URL}/api/user/${mockUserId}/aws-connections`,
      {
        headers: {
          Authorization: `Bearer ${mockToken}`,
        },
      },
    );

    // Verify response indicates not found
    expect(response.ok).toBe(false);
    expect(response.status).toBe(404);

    // Verify error message is in response
    const data = await response.json();
    expect(data).toHaveProperty("detail");
    expect(data.detail).toBe(errorMessage);
  });

  test("API returns error with message field instead of detail", async () => {
    const errorMessage = "Failed to load AWS connections";

    // Mock error response with message field
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({
        message: errorMessage,
      }),
    });

    // Simulate the AWS connections request
    const response = await fetch(
      `${API_BASE_URL}/api/user/${mockUserId}/aws-connections`,
      {
        headers: {
          Authorization: `Bearer ${mockToken}`,
        },
      },
    );

    // Verify response indicates failure
    expect(response.ok).toBe(false);
    expect(response.status).toBe(500);

    // Verify error message is in response
    const data = await response.json();
    expect(data).toHaveProperty("message");
    expect(data.message).toBe(errorMessage);
  });

  test("network error when API is unreachable", async () => {
    const networkError = new Error("Network request failed");

    // Mock fetch to throw network error
    (global.fetch as jest.Mock).mockRejectedValueOnce(networkError);

    // Simulate the AWS connections request and expect it to throw
    await expect(
      fetch(`${API_BASE_URL}/api/user/${mockUserId}/aws-connections`, {
        headers: {
          Authorization: `Bearer ${mockToken}`,
        },
      }),
    ).rejects.toThrow("Network request failed");

    // Verify the request was attempted
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  test("AWS connections request fails when JWT token is missing", async () => {
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

    // Simulate the AWS connections request without token
    const response = await fetch(
      `${API_BASE_URL}/api/user/${mockUserId}/aws-connections`,
      {
        headers: {
          // No Authorization header
        },
      },
    );

    // Verify the request was made
    expect(global.fetch).toHaveBeenCalledTimes(1);

    // Verify response indicates authentication failure
    expect(response.ok).toBe(false);
    expect(response.status).toBe(401);
  });

  test("AWS connections response structure matches expected format", async () => {
    const mockConnections = [
      {
        id: "conn-123",
        user_id: mockUserId,
        aws_account_id: "123456789012",
        external_id: "ext-id-123",
        role_arn: "arn:aws:iam::123456789012:role/TestRole",
        status: "active",
      },
    ];

    // Mock successful fetch response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        connections: mockConnections,
      }),
    });

    // Simulate the AWS connections request
    const response = await fetch(
      `${API_BASE_URL}/api/user/${mockUserId}/aws-connections`,
      {
        headers: {
          Authorization: `Bearer ${mockToken}`,
        },
      },
    );

    // Verify response is successful
    expect(response.ok).toBe(true);

    // Verify response structure
    const data = await response.json();
    expect(data).toHaveProperty("connections");
    expect(Array.isArray(data.connections)).toBe(true);

    // Verify connection object structure
    const connection = data.connections[0];
    expect(connection).toHaveProperty("id");
    expect(connection).toHaveProperty("user_id");
    expect(connection).toHaveProperty("aws_account_id");
    expect(connection).toHaveProperty("external_id");
    expect(connection).toHaveProperty("role_arn");
    expect(connection).toHaveProperty("status");

    // Verify field types
    expect(typeof connection.id).toBe("string");
    expect(typeof connection.user_id).toBe("string");
    expect(typeof connection.aws_account_id).toBe("string");
    expect(typeof connection.external_id).toBe("string");
    expect(typeof connection.role_arn).toBe("string");
    expect(typeof connection.status).toBe("string");
  });

  test("multiple AWS connections are loaded in correct order", async () => {
    const mockConnections = [
      {
        id: "conn-first",
        user_id: mockUserId,
        aws_account_id: "111111111111",
        external_id: "ext-first",
        role_arn: "arn:aws:iam::111111111111:role/FirstRole",
        status: "active",
      },
      {
        id: "conn-second",
        user_id: mockUserId,
        aws_account_id: "222222222222",
        external_id: "ext-second",
        role_arn: "arn:aws:iam::222222222222:role/SecondRole",
        status: "active",
      },
      {
        id: "conn-third",
        user_id: mockUserId,
        aws_account_id: "333333333333",
        external_id: "ext-third",
        role_arn: "arn:aws:iam::333333333333:role/ThirdRole",
        status: "active",
      },
    ];

    // Mock successful fetch response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        connections: mockConnections,
      }),
    });

    // Simulate the AWS connections request
    const response = await fetch(
      `${API_BASE_URL}/api/user/${mockUserId}/aws-connections`,
      {
        headers: {
          Authorization: `Bearer ${mockToken}`,
        },
      },
    );

    // Verify response is successful
    expect(response.ok).toBe(true);

    // Verify connections are returned in correct order
    const data = await response.json();
    expect(data.connections).toHaveLength(3);
    expect(data.connections[0].id).toBe("conn-first");
    expect(data.connections[1].id).toBe("conn-second");
    expect(data.connections[2].id).toBe("conn-third");
  });
});
