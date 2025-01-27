// File: frontend/components/ActivityLog.js
import { useEffect, useState } from "react";
import { Box, Text, useColorModeValue } from "@chakra-ui/react";

export default function ActivityLog({ deploymentId }) {
  const [logs, setLogs] = useState([]);
  const bgColor = useColorModeValue("gray.200", "gray.700");
  const textColor = useColorModeValue("black", "white");

  useEffect(() => {
    if (!deploymentId) return;

    const wsUrl = `ws://localhost:8000/deployments/logs/ws/${deploymentId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("WebSocket connected for deployment", deploymentId);
    };

    ws.onmessage = (event) => {
      setLogs((prev) => [...prev, event.data]);
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    ws.onclose = () => {
      console.log("WebSocket closed for deployment", deploymentId);
    };

    return () => {
      ws.close();
    };
  }, [deploymentId]);

  return (
    <Box mt={4} p={4} bg={bgColor} color={textColor} maxH="400px" overflowY="auto">
      <Text fontWeight="bold" mb={2}>
        Deployment Logs (ID: {deploymentId}):
      </Text>
      {logs.map((log, idx) => {
        // Check if this line starts with "AI Plan" to highlight it
        if (log.trim().startsWith("AI Plan")) {
          return (
            <Text key={idx} fontSize="sm" fontWeight="bold" color="orange.300">
              {log}
            </Text>
          );
        }
        return (
          <Text key={idx} fontSize="sm">
            {log}
          </Text>
        );
      })}
    </Box>
  );
}
