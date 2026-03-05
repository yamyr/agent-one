import unittest


class TestNotifyPeerToolSchema(unittest.TestCase):
    """Tests for NOTIFY_PEER_TOOL definition and registration."""

    def test_notify_peer_tool_exists(self):
        """NOTIFY_PEER_TOOL should be defined in agent module."""
        from app.agent import NOTIFY_PEER_TOOL

        self.assertEqual(NOTIFY_PEER_TOOL["function"]["name"], "notify_peer")

    def test_notify_peer_in_rover_tools(self):
        """NOTIFY_PEER_TOOL should be in ROVER_TOOLS list."""
        from app.agent import ROVER_TOOLS

        tool_names = [t["function"]["name"] for t in ROVER_TOOLS]
        self.assertIn("notify_peer", tool_names)

    def test_notify_peer_has_required_params(self):
        """notify_peer should require target_id and message params."""
        from app.agent import NOTIFY_PEER_TOOL

        params = NOTIFY_PEER_TOOL["function"]["parameters"]
        self.assertIn("target_id", params["properties"])
        self.assertIn("message", params["properties"])
        self.assertEqual(params["required"], ["target_id", "message"])


class TestExecuteNotifyPeer(unittest.TestCase):
    """Tests for _execute_notify_peer action execution."""

    def setUp(self):
        from app.world import world, AGENT_MESSAGES

        # Clear messages
        AGENT_MESSAGES.clear()
        # Reset rover state
        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["mission"] = {
            "objective": "Explore",
            "plan": [],
        }
        # Ensure rover-2 exists
        if "rover-2" not in world.state["agents"]:
            world.state["agents"]["rover-2"] = {
                "type": "rover",
                "position": [5, 5],
                "battery": 1.0,
                "mission": {"objective": "Explore", "plan": []},
                "visited": [[5, 5]],
                "memory": [],
                "inventory": [],
                "revealed": [],
                "solar_panels_remaining": 3,
            }
        else:
            world.state["agents"]["rover-2"]["type"] = "rover"
            world.state["agents"]["rover-2"]["battery"] = 1.0

    def test_notify_peer_success(self):
        """Successful peer message should deduct battery and deliver message."""
        from app.world import execute_action, get_unread_messages

        result = execute_action(
            "rover-mistral",
            "notify_peer",
            {
                "target_id": "rover-2",
                "message": "Found rich vein at (12,8)!",
            },
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["target"], "rover-2")
        self.assertEqual(result["message"], "Found rich vein at (12,8)!")

        # Message should be in target's inbox
        messages = get_unread_messages("rover-2")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["from"], "rover-mistral")
        self.assertEqual(messages[0]["message"], "Found rich vein at (12,8)!")

    def test_notify_peer_deducts_battery(self):
        """notify_peer should deduct BATTERY_COST_NOTIFY from sender."""
        from app.world import execute_action, world, BATTERY_COST_NOTIFY

        initial_battery = world.state["agents"]["rover-mistral"]["battery"]
        execute_action(
            "rover-mistral",
            "notify_peer",
            {
                "target_id": "rover-2",
                "message": "test",
            },
        )
        new_battery = world.state["agents"]["rover-mistral"]["battery"]
        self.assertAlmostEqual(new_battery, initial_battery - BATTERY_COST_NOTIFY, places=4)

    def test_notify_peer_self_targeting_fails(self):
        """Cannot send message to yourself."""
        from app.world import execute_action

        result = execute_action(
            "rover-mistral",
            "notify_peer",
            {
                "target_id": "rover-mistral",
                "message": "hello me",
            },
        )
        self.assertFalse(result["ok"])
        self.assertIn("yourself", result["error"])

    def test_notify_peer_nonexistent_target_fails(self):
        """Cannot send to non-existent agent."""
        from app.world import execute_action

        result = execute_action(
            "rover-mistral",
            "notify_peer",
            {
                "target_id": "rover-ghost",
                "message": "hello",
            },
        )
        self.assertFalse(result["ok"])
        self.assertIn("Unknown", result["error"])

    def test_notify_peer_station_target_fails(self):
        """Cannot send peer message to station — use notify instead."""
        from app.world import execute_action

        result = execute_action(
            "rover-mistral",
            "notify_peer",
            {
                "target_id": "station",
                "message": "hello station",
            },
        )
        self.assertFalse(result["ok"])
        self.assertIn("notify", result["error"].lower())

    def test_notify_peer_drone_target_fails(self):
        """Cannot send peer message to drones."""
        from app.world import execute_action

        result = execute_action(
            "rover-mistral",
            "notify_peer",
            {
                "target_id": "drone-mistral",
                "message": "hello drone",
            },
        )
        self.assertFalse(result["ok"])
        self.assertIn("drone", result["error"].lower())

    def test_notify_peer_empty_message_fails(self):
        """Empty message should fail."""
        from app.world import execute_action

        result = execute_action(
            "rover-mistral",
            "notify_peer",
            {
                "target_id": "rover-2",
                "message": "",
            },
        )
        self.assertFalse(result["ok"])
        self.assertIn("Empty", result["error"])

    def test_notify_peer_low_battery_fails(self):
        """Should fail when battery is too low."""
        from app.world import execute_action, world

        world.state["agents"]["rover-mistral"]["battery"] = 0.001
        result = execute_action(
            "rover-mistral",
            "notify_peer",
            {
                "target_id": "rover-2",
                "message": "help!",
            },
        )
        self.assertFalse(result["ok"])
        self.assertIn("battery", result["error"].lower())

    def test_notify_peer_no_target_id_fails(self):
        """Missing target_id should fail."""
        from app.world import execute_action

        result = execute_action(
            "rover-mistral",
            "notify_peer",
            {
                "message": "hello",
            },
        )
        self.assertFalse(result["ok"])
        self.assertIn("target_id", result["error"])


class TestPeerMessageDelivery(unittest.TestCase):
    """Tests for message delivery via send_agent_message."""

    def setUp(self):
        from app.world import AGENT_MESSAGES

        AGENT_MESSAGES.clear()

    def test_message_appears_in_unread(self):
        """After send_agent_message, get_unread_messages returns it."""
        from app.world import send_agent_message, get_unread_messages

        send_agent_message("rover-mistral", "rover-2", "Test message")
        unread = get_unread_messages("rover-2")
        self.assertEqual(len(unread), 1)
        self.assertEqual(unread[0]["from"], "rover-mistral")
        self.assertEqual(unread[0]["message"], "Test message")

    def test_message_marked_read_after_retrieval(self):
        """Messages should be marked read after get_unread_messages."""
        from app.world import send_agent_message, get_unread_messages

        send_agent_message("rover-mistral", "rover-2", "Test")
        get_unread_messages("rover-2")
        # Second call should return empty
        unread2 = get_unread_messages("rover-2")
        self.assertEqual(len(unread2), 0)

    def test_multiple_messages_delivered(self):
        """Multiple messages from different senders should all arrive."""
        from app.world import send_agent_message, get_unread_messages, world

        # Ensure rover-large exists
        if "rover-large" not in world.state["agents"]:
            world.state["agents"]["rover-large"] = {
                "type": "rover",
                "position": [0, 0],
                "battery": 1.0,
                "mission": {"objective": "Explore", "plan": []},
                "visited": [],
                "memory": [],
                "inventory": [],
                "revealed": [],
                "solar_panels_remaining": 3,
            }
        send_agent_message("rover-mistral", "rover-2", "Message 1")
        send_agent_message("rover-large", "rover-2", "Message 2")
        unread = get_unread_messages("rover-2")
        self.assertEqual(len(unread), 2)
        senders = {m["from"] for m in unread}
        self.assertEqual(senders, {"rover-mistral", "rover-large"})


class TestPeerCommunicationPrompt(unittest.TestCase):
    """Tests for PEER COMMUNICATION section in rover prompt."""

    def setUp(self):
        from app.world import world

        world.state["agents"]["rover-mistral"]["position"] = [10, 10]
        world.state["agents"]["rover-mistral"]["battery"] = 1.0
        world.state["agents"]["rover-mistral"]["mission"] = {
            "objective": "Explore the terrain",
            "plan": [],
        }
        world.state["agents"]["rover-mistral"]["visited"] = [[10, 10]]

    def test_prompt_contains_peer_communication_section(self):
        """Rover context should include PEER COMMUNICATION section."""
        from app.agent import MistralRoverReasoner
        from app.world import world

        agent = MistralRoverReasoner(agent_id="rover-mistral", world=world)
        ctx = agent._build_context()
        self.assertIn("PEER COMMUNICATION", ctx)

    def test_prompt_lists_peer_rover_ids(self):
        """PEER COMMUNICATION section should list other rover IDs."""
        from app.agent import MistralRoverReasoner
        from app.world import world

        # Ensure rover-2 exists
        if "rover-2" not in world.state["agents"]:
            world.state["agents"]["rover-2"] = {
                "type": "rover",
                "position": [5, 5],
                "battery": 1.0,
                "mission": {"objective": "Explore", "plan": []},
                "visited": [],
                "memory": [],
                "inventory": [],
                "revealed": [],
                "solar_panels_remaining": 3,
            }
        agent = MistralRoverReasoner(agent_id="rover-mistral", world=world)
        ctx = agent._build_context()
        self.assertIn("rover-2", ctx)

    def test_prompt_does_not_list_self(self):
        """PEER COMMUNICATION should not list the rover itself as a peer."""
        from app.agent import MistralRoverReasoner
        from app.world import world

        agent = MistralRoverReasoner(agent_id="rover-mistral", world=world)
        ctx = agent._build_context()
        # Find the PEER COMMUNICATION section and check self is not listed as a peer
        peer_section_start = ctx.find("PEER COMMUNICATION")
        if peer_section_start >= 0:
            peer_section = ctx[peer_section_start : peer_section_start + 500]
            peers_line = [line for line in peer_section.split("\n") if "Available peers:" in line]
            if peers_line:
                self.assertNotIn("rover-mistral", peers_line[0])

    def test_prompt_does_not_list_station_as_peer(self):
        """Station should not appear in PEER COMMUNICATION peers list."""
        from app.agent import MistralRoverReasoner
        from app.world import world

        agent = MistralRoverReasoner(agent_id="rover-mistral", world=world)
        ctx = agent._build_context()
        peer_section_start = ctx.find("PEER COMMUNICATION")
        if peer_section_start >= 0:
            peer_section = ctx[peer_section_start : peer_section_start + 500]
            peers_line = [line for line in peer_section.split("\n") if "Available peers:" in line]
            if peers_line:
                self.assertNotIn("station", peers_line[0])
