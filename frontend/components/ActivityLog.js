import { useEffect, useState } from "react";
import { Box, Text } from "@chakra-ui/react";

export default function ActivityLog({ deploymentId }) {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    if (!deploymentId) return;

    // Create a new WebSocket connecting to the parameterized endpoint
    const wsUrl = `ws://localhost:8000/deployments/logs/ws/${deploymentId}`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      setLogs((prev) => [...prev, event.data]);
    };

    ws.onclose = () => {
      console.log("WebSocket closed");
    };

    return () => {
      ws.close();
    };
  }, [deploymentId]);

  return (
    <Box mt={4} p={4} bg="gray.700" color="white">
      <Text fontWeight="bold">Deployment Logs:</Text>
      {logs.map((log, index) => (
        <Text key={index} fontSize="sm">
          {log}
        </Text>
      ))}
    </Box>
  );
}
