// File: frontend/pages/wizard.js

import { useState } from "react";
import { useMutation } from "react-query";
import {
  Box,
  Button,
  Input,
  FormControl,
  FormLabel,
  Text,
  Heading,
  Select,
  VStack,
  HStack,
  Textarea,
  Spinner,
} from "@chakra-ui/react";
import { useRouter } from "next/router";
import {
  createConversation,
  generateCode,
  startDeployment,
} from "../utils/api";

function WizardStep1({ wizardData, setWizardData, onNext }) {
  return (
    <Box>
      <Heading size="md" mb={4}>Step 1: Basic Details</Heading>
      <FormControl mb={4}>
        <FormLabel>Service Name</FormLabel>
        <Input
          placeholder="my-service"
          value={wizardData.serviceName}
          onChange={(e) =>
            setWizardData({ ...wizardData, serviceName: e.target.value })
          }
        />
      </FormControl>
      <FormControl mb={4}>
        <FormLabel>Port Number</FormLabel>
        <Input
          type="number"
          value={wizardData.port}
          onChange={(e) =>
            setWizardData({ ...wizardData, port: parseInt(e.target.value) || 9000 })
          }
        />
      </FormControl>
      <FormControl mb={4}>
        <FormLabel>Short Description</FormLabel>
        <Textarea
          placeholder="Briefly describe what this service does."
          value={wizardData.description}
          onChange={(e) =>
            setWizardData({ ...wizardData, description: e.target.value })
          }
        />
      </FormControl>
      <Button colorScheme="blue" onClick={onNext}>
        Next
      </Button>
    </Box>
  );
}

function WizardStep2({ wizardData, setWizardData, onNext, onBack }) {
  const [tempPath, setTempPath] = useState("");
  const [tempMethod, setTempMethod] = useState("GET");
  const [tempDesc, setTempDesc] = useState("");

  const addEndpoint = () => {
    if (!tempPath) return;
    const newEndpoint = {
      path: tempPath,
      method: tempMethod,
      description: tempDesc,
    };
    setWizardData({
      ...wizardData,
      endpoints: [...wizardData.endpoints, newEndpoint],
    });
    setTempPath("");
    setTempMethod("GET");
    setTempDesc("");
  };

  return (
    <Box>
      <Heading size="md" mb={4}>Step 2: Define Endpoints</Heading>
      {wizardData.endpoints.map((ep, idx) => (
        <Box key={idx} bg="gray.700" p={3} mb={2} borderRadius="md">
          <Text><strong>Path:</strong> {ep.path}</Text>
          <Text><strong>Method:</strong> {ep.method}</Text>
          <Text><strong>Description:</strong> {ep.description}</Text>
        </Box>
      ))}
      <FormControl mb={2}>
        <FormLabel>Path</FormLabel>
        <Input
          placeholder="/items"
          value={tempPath}
          onChange={(e) => setTempPath(e.target.value)}
        />
      </FormControl>
      <FormControl mb={2}>
        <FormLabel>Method</FormLabel>
        <Select
          value={tempMethod}
          onChange={(e) => setTempMethod(e.target.value)}
        >
          <option value="GET">GET</option>
          <option value="POST">POST</option>
          <option value="PUT">PUT</option>
          <option value="DELETE">DELETE</option>
        </Select>
      </FormControl>
      <FormControl mb={4}>
        <FormLabel>Short Description</FormLabel>
        <Textarea
          value={tempDesc}
          onChange={(e) => setTempDesc(e.target.value)}
        />
      </FormControl>
      <Button colorScheme="orange" onClick={addEndpoint} mb={4}>
        Add Endpoint
      </Button>
      <HStack>
        <Button variant="outline" onClick={onBack}>
          Back
        </Button>
        <Button colorScheme="blue" onClick={onNext}>
          Next
        </Button>
      </HStack>
    </Box>
  );
}

function WizardReview({ wizardData, onBack, onDeploy, isDeploying }) {
  return (
    <Box>
      <Heading size="md" mb={4}>Step 3: Review & Confirm</Heading>
      <Text>
        <strong>Service Name:</strong> {wizardData.serviceName}
      </Text>
      <Text>
        <strong>Port:</strong> {wizardData.port}
      </Text>
      <Text mb={2}>
        <strong>Description:</strong> {wizardData.description}
      </Text>
      <Text fontWeight="semibold">Endpoints:</Text>
      {wizardData.endpoints.length === 0 && <Text>No endpoints defined yet.</Text>}
      {wizardData.endpoints.map((ep, idx) => (
        <Box key={idx} bg="gray.700" p={3} my={2} borderRadius="md">
          <Text>Path: {ep.path}</Text>
          <Text>Method: {ep.method}</Text>
          <Text>Description: {ep.description}</Text>
        </Box>
      ))}

      <HStack mt={4}>
        <Button variant="outline" onClick={onBack}>
          Back
        </Button>
        <Button
          colorScheme="blue"
          onClick={onDeploy}
          isLoading={isDeploying}
        >
          Generate & Deploy
        </Button>
      </HStack>
    </Box>
  );
}

export default function Wizard() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [wizardData, setWizardData] = useState({
    serviceName: "",
    port: 9000,
    description: "",
    endpoints: [],
  });
  const [isDeploying, setIsDeploying] = useState(false);

  const { mutateAsync: doCreateConversation } = useMutation(createConversation);
  const { mutateAsync: doGenerateCode } = useMutation(generateCode);
  const { mutateAsync: doStartDeployment } = useMutation(startDeployment);

  const handleNext = () => setStep(step + 1);
  const handleBack = () => setStep(step - 1);

  const handleDeploy = async () => {
    try {
      setIsDeploying(true);

      // (a) Build a "spec" from the wizard data
      const flexSpec = {
        service_name: wizardData.serviceName || "wizard-service",
        port: wizardData.port || 9000,
        endpoints: wizardData.endpoints,
        description: wizardData.description,
      };

      // (b) Create a conversation
      const specMessage = {
        role: "user",
        content: JSON.stringify(flexSpec, null, 2),
      };
      const convoRes = await doCreateConversation({ messages: [specMessage] });
      const conversationId = convoRes.conversation_id;

      // (c) Generate code
      const genRes = await doGenerateCode({
        conversation_id: conversationId,
        prompt: "Generate code for the above Flex Spec."
      });

      // (d) Start deployment
      const uniqueAppName = `flex-fastapi-app-${Math.floor(1000 + Math.random() * 9000)}`;
      await doStartDeployment({
        conversation_id: conversationId,
        app_name: uniqueAppName,
        max_iterations: 5,
        port_number: wizardData.port,
        trouble_mode: false,
      });

      // (e) Navigate to /services
      router.push("/services");
    } catch (err) {
      console.error("Error in wizard deployment pipeline:", err);
      alert(`Deployment error: ${err.message}`);
    } finally {
      setIsDeploying(false);
    }
  };

  return (
    <Box maxW="lg" mx="auto" mt={10} bg="gray.800" p={6} borderRadius="md">
      <Heading mb={4}>Service Creation Wizard</Heading>

      {step === 1 && (
        <WizardStep1
          wizardData={wizardData}
          setWizardData={setWizardData}
          onNext={handleNext}
        />
      )}
      {step === 2 && (
        <WizardStep2
          wizardData={wizardData}
          setWizardData={setWizardData}
          onNext={handleNext}
          onBack={handleBack}
        />
      )}
      {step === 3 && (
        <WizardReview
          wizardData={wizardData}
          onBack={handleBack}
          onDeploy={handleDeploy}
          isDeploying={isDeploying}
        />
      )}
    </Box>
  );
}
