import json
import random
import time
import asyncio
import aiohttp
import zmq
import zmq.asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import env
import econ2json
import html_extractor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Person:
    occupation: str
    group_name: str
    group_focus: str
    meetup_frequency: str
    online_community: str
    contact_name: str
    usual_venues: str
    events_page: str
    website: str
    legal_status: str
    extracted_text: Optional[str] = None

@dataclass
class ConversationMessage:
    person_name: str
    group_name: str
    message: str
    timestamp: datetime

@dataclass
class Conversation:
    id: str
    participants: List[Person]
    messages: List[ConversationMessage]
    topic: str

class WebContentExtractor:
    """Extracts text content from web pages"""
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={'User-Agent': 'Mozilla/5.0 (compatible; ContentBot/1.0)'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

class DeepSeekClient:
    """Client for interacting with DeepSeek API"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def generate_persona_response(self, person: Person, conversation_context: str, topic: str) -> str:
        """Generate a response as if the AI is the specified person"""
        
        persona_prompt = f"""
You are {person.contact_name} from {person.group_name}, a {person.group_focus} focused group.
Your group meets {person.meetup_frequency} at venues like {person.usual_venues}.
Your group's legal status is {person.legal_status}.

{f"Additional context about your organization: {person.extracted_text[:2000]}" if person.extracted_text else ""}

You are participating in a conversation about: {topic}

Previous conversation context:
{conversation_context}

Respond as {person.contact_name} would, drawing from your expertise in {person.group_focus} and your experience with {person.group_name}. 
Keep your response conversational, authentic, and under 200 words.
"""

        try:
            async with self.session.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": persona_prompt},
                        {"role": "user", "content": f"Please contribute to this conversation about {topic}"}
                    ],
                    "max_tokens": 300,
                    "temperature": 0.7
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['choices'][0]['message']['content'].strip()
                else:
                    logger.error(f"DeepSeek API error: {response.status}")
                    return f"[Error generating response for {person.contact_name}]"
                    
        except Exception as e:
            logger.error(f"Failed to generate response for {person.contact_name}: {e}")
            return f"[{person.contact_name} from {person.group_name} nods thoughtfully]"

class ConversationFacilitator:
    """Manages AI conversations between personas"""
    
    def __init__(self, deepseek_client: DeepSeekClient):
        self.deepseek_client = deepseek_client
        
    def create_conversations(self, people: List[Person]) -> List[Conversation]:
        """Randomly assign people to conversations of 2-6 participants"""
        conversations = []
        remaining_people = people.copy()
        random.shuffle(remaining_people)
        
        conversation_topics = [
            "The future of tech meetups and community building",
            "Automation's impact on local workforce development", 
            "Building inclusive tech communities",
            "Remote vs in-person collaboration",
            "Skills development in emerging technologies",
            "Networking strategies for tech professionals"
        ]
        
        conv_id = 1
        while remaining_people:
            # Random group size between 2-6, but don't exceed remaining people
            group_size = min(random.randint(2, 6), len(remaining_people))
            participants = remaining_people[:group_size]
            remaining_people = remaining_people[group_size:]
            
            conversation = Conversation(
                id=f"conv_{conv_id:03d}",
                participants=participants,
                messages=[],
                topic=random.choice(conversation_topics)
            )
            conversations.append(conversation)
            conv_id += 1
            
        return conversations
    
    async def facilitate_conversation_round(self, conversation: Conversation) -> None:
        """Run one round of conversation where each participant contributes"""
        
        for i, person in enumerate(conversation.participants):
            # Build context from previous messages
            context = "\n".join([
                f"{msg.person_name}: {msg.message}" 
                for msg in conversation.messages[-5:]  # Last 5 messages for context
            ])
            
            # Generate response for this person
            response = await self.deepseek_client.generate_persona_response(
                person, context, conversation.topic
            )
            
            # Add message to conversation
            message = ConversationMessage(
                person_name=person.contact_name,
                group_name=person.group_name,
                message=response,
                timestamp=datetime.now()
            )
            conversation.messages.append(message)
            
            logger.info(f"[{conversation.id}] {person.contact_name}: {response[:100]}...")
            
            # Small delay between responses to seem more natural
            await asyncio.sleep(0.5)

class ZMQPublisher:
    """Publishes conversation data via ZMQ"""
    
    def __init__(self, port: int = 5555):
        self.port = port
        self.context = None
        self.socket = None
    
    async def __aenter__(self):
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind(f"tcp://*:{self.port}")
        logger.info(f"ZMQ Publisher bound to port {self.port}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
    
    async def publish_conversation(self, conversation: Conversation):
        """Publish conversation data to ZMQ subscribers"""
        data = {
            "type": "conversation",
            "conversation_id": conversation.id,
            "topic": conversation.topic,
            "participants": [
                {
                    "name": p.contact_name,
                    "group": p.group_name,
                    "focus": p.group_focus
                } for p in conversation.participants
            ],
            "messages": [
                {
                    "person_name": msg.person_name,
                    "group_name": msg.group_name,
                    "message": msg.message,
                    "timestamp": msg.timestamp.isoformat()
                } for msg in conversation.messages
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        await self.socket.send_multipart([
            b"conversation",
            json.dumps(data, indent=2).encode('utf-8')
        ])
        logger.info(f"Published conversation {conversation.id} to ZMQ")

async def main():
    # Configuration
    ZMQ_PORT = 5555
    
    # Sample data (replace with your actual data loading)
    with open('Baltimore Tech Economy - Tech Groups.csv', 'r') as f:
        people_data = econ2json(f.read())

    # Convert data to Person objects
    people = []
    for data in people_data:
        person = Person(
            occupation=data["Occupation"],
            group_name=data["Group Name"],
            group_focus=data["Group focus"],
            meetup_frequency=data["Meetup Frequency"],
            online_community=data["Online Community"],
            contact_name=data["Contact Name"],
            usual_venues=data["Usual Venues"],
            events_page=data["Events Page"],
            website=data["Website"],
            legal_status=data["Legal status"]
        )
        people.append(person)
    
    logger.info(f"Loaded {len(people)} people")
    
    # Extract website content
    async with WebContentExtractor() as extractor:
        for person in people:
            if person.website:
                logger.info(f"Extracting content from {person.website}")
                person.extracted_text = await extractor.extract_text_from_html(person.website)
    
    # Create conversations and facilitate them
    async with DeepSeekClient(env.DEEPSEEK_API_KEY) as deepseek_client:
        facilitator = ConversationFacilitator(deepseek_client)
        conversations = facilitator.create_conversations(people)
        
        logger.info(f"Created {len(conversations)} conversations")
        
        # Publish conversations via ZMQ
        async with ZMQPublisher(ZMQ_PORT) as publisher:
            for conversation in conversations:
                logger.info(f"Facilitating conversation {conversation.id}: {conversation.topic}")
                await facilitator.facilitate_conversation_round(conversation)
                await publisher.publish_conversation(conversation)
                
                # Brief pause between conversations
                await asyncio.sleep(1)
    
    logger.info("All conversations completed and published!")

if __name__ == "__main__":
    # Required dependencies:
    # pip install aiohttp beautifulsoup4 pyzmq
    
    asyncio.run(main())