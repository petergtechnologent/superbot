import { useEffect, useState } from "react";
import { Box, Text } from "@chakra-ui/react";

export default function ActivityLog({ deploymentId }) {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    if (!deploymentId) return;

    // Adjust for your actual host/port, e.g. ws://localhost:8000
    const ws = new WebSocket("ws://localhost:8000/deployments/logs/ws");
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
    <Box mt={4} p={4} bg="gray.700">
      <Text>Deployment Logs:</Text>
      {logs.map((log, index) => (
        <Text key={index}>{log}</Text>
      ))}
    </Box>
  );
}
