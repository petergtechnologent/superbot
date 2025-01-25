import { useQuery } from "react-query";
import { getConversations } from "../utils/api";
import { Box, Heading, Text } from "@chakra-ui/react";

export default function History() {
  const { data, isLoading } = useQuery("conversations", getConversations);

  if (isLoading) return <Text>Loading...</Text>;
  if (!data) return <Text>No history yet.</Text>;

  return (
    <Box>
      <Heading>Past Conversations</Heading>
      {data.map((conv) => (
        <Box key={conv._id} p={4} my={2} bg="gray.700">
          <Text>Conversation ID: {conv._id}</Text>
          <Text>Messages: {JSON.stringify(conv.messages)}</Text>
        </Box>
      ))}
    </Box>
  );
}
