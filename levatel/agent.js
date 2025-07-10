
import { getAI, getGenerativeModel, GoogleAIBackend } from "https://www.gstatic.com/firebasejs/11.10.0/firebase-ai.js";
import { firebaseConfig } from './firebase-config.js';
import { initializeApp } from "https://www.gstatic.com/firebasejs/11.10.0/firebase-app.js";

// Initialize Firebase AI
console.log('Initializing Firebase app...');
const firebaseApp = initializeApp(firebaseConfig);
console.log('Firebase app initialized, setting up AI service...');
const ai = getAI(firebaseApp, { backend: new GoogleAIBackend() });
console.log('AI service initialized, creating model...');
const model = getGenerativeModel(ai, { model: "gemini-2.5-flash" });
console.log('Gemini model ready:', model);

let userOrder = [];
let menu = {};
let availableServices = [];
let activeService = '';

// Load menu data at startup
(async () => {
  try {
    const response = await fetch('./menu.json');
    menu = await response.json();
    availableServices = Object.keys(menu);
    activeService = availableServices[0];
  } catch (error) {
    console.error('Error loading menu:', error);
  }
})();

export function updateOrderDisplay() {
  const orderTable = document.getElementById('orderTable');
  if (!orderTable) return;

  // Clear existing rows
  orderTable.innerHTML = '';

  // Add header row
  const headerRow = document.createElement('tr');
  headerRow.innerHTML = '<th>Item</th><th>Notes</th>';
  orderTable.appendChild(headerRow);

  // Add order items
  userOrder.forEach(item => {
    const row = document.createElement('tr');
    const itemName = Object.keys(item)[0];
    const notes = item[itemName];
    row.innerHTML = `<td>${itemName}</td><td>${notes}</td>`;
    orderTable.appendChild(row);
  });
}


// Menu data is now loaded in the async IIFE at the top

const aiActions = {
  "CHANGE_SERVICE": "CHANGE_SERVICE SERVICENAME ; Triggered when the user wants to switch to a different restaurant or service.",
  "POPULAR_ITEMS": "POPULAR_ITEMS ; Used when the user is hesitant or undecided — instructs the client to display the top 3 popular items from the currently active service.",
  "POPULAR_SERVICES": "POPULAR_SERVICES ; Used when the user doesn't know which service they want — instructs the client to list popular or available services.",
  "ADD_ITEM": "ADD_ITEM ITEMNAME, NOTE ; Adds the specified item to the user's order. Optionally include a note (e.g., 'no onions'). The client should assign a unique item number.",
  "REMOVE_ITEM": "REMOVE_ITEM ITEMNAME #N ; Removes the specified item (with number #N) from the user's order.",
  "ADD_NOTE": "ADD_NOTE NOTE ; Adds a note or instruction (e.g., 'extra spicy') to the last added item or to the currently selected item.",
  "REQUEST_CONFIRMATION": "REQUEST_CONFIRMATION ; Asks the user to confirm if their order is correct and ready to be submitted.",
  "SUBMIT_ORDER": "SUBMIT_ORDER ; Tells the client browser to submit the current order."
};

const prompt = `
You help users order food. Read the user's message and pick ONE action.

Available services: AVAILABLE_SERVICES_REPLACE
Current service: ACTIVE_SERVICE_REPLACE
Menu items: MENU_ITEMS_REPLACE

ACTIONS:
- CHANGE_SERVICE [service name]
- ADD_ITEM [item name], [note]
- REMOVE_ITEM [item name] #[number]
- ADD_NOTE [note]
- POPULAR_ITEMS
- POPULAR_SERVICES
- REQUEST_CONFIRMATION
- SUBMIT_ORDER

RULES:
- Return only the action
- Use exact item names from menu
- Use exact service names from list, NOT the form supplied by the user

User said: "{user_input}"

Action:`;


export async function processUserRequest(requestText) {
  // Get current menu data
  const response = await fetch('./menu.json');
  const menu = await response.json();
  
  // Update prompt with current data
  const currentPrompt = prompt
    .replace('{user_input}', requestText)
    .replace('AVAILABLE_SERVICES_REPLACE', availableServices.map(s => `- ${s}`).join('\n'))
    .replace('MENU_ITEMS_REPLACE', JSON.stringify(menu[activeService] || []))

  const result = await model.generateContent({
    contents: [
      {
        role: "user",
        parts: [{ text: currentPrompt }],
      },
    ],
  });
  
  const action = result.response.text();
  const actionText = await handleAction(action);
  return actionText;
}

export async function handleAction(action) {
  let displayText = null;
  
  if (action.startsWith('ADD_ITEM')) {
    const parts = action.split(',');
    const itemName = parts[0].replace('ADD_ITEM', '').trim();
    const note = parts.length > 1 ? parts[1].trim() : '';
    const itemNumber = userOrder.length + 1;
    userOrder.push({ [`${itemName} #${itemNumber}`]: note });
    displayText = `Added ${itemName} to your order`;
  } 
  else if (action.startsWith('REMOVE_ITEM')) {
    const itemKey = action.replace('REMOVE_ITEM', '').trim();
    userOrder = userOrder.filter(item => !Object.keys(item)[0].includes(itemKey));
    displayText = `Removed ${itemKey} from your order`;
  }
  else if (action.startsWith('ADD_NOTE')) {
    const note = action.replace('ADD_NOTE', '').trim();
    if (userOrder.length > 0) {
      const lastItem = userOrder[userOrder.length - 1];
      const key = Object.keys(lastItem)[0];
      lastItem[key] = note;
      displayText = `Added note: ${note}`;
    }
  }
  else if (action === 'POPULAR_ITEMS') {
    const response = await fetch('./menu.json');
    const menu = await response.json();
    const items = menu[activeService]?.slice(0, 3) || [];
    const itemsText = items.map(item => 
      `${Object.keys(item)[0]}: ${Object.values(item)[0]}`
    ).join('\n');
    displayText = `Popular items from ${activeService}:\n${itemsText}`;
  }
  else if (action === 'POPULAR_SERVICES') {
    const servicesText = availableServices.join('\n');
    displayText = 'Available services:\n' + servicesText;
  }
  else if (action.startsWith('CHANGE_SERVICE')) {
    const serviceName = action.replace('CHANGE_SERVICE', '').trim();
    activeService = serviceName;
    displayText = `Switched to ${serviceName}`;
  }
  else if (action === 'REQUEST_CONFIRMATION') {
    displayText = 'Shall I place this order with card ending in 5555? If so, say Submit';
  }
  else if (action === 'SUBMIT_ORDER') {
    displayText = 'Order submitted successfully!';
  }
  else {
    displayText = action; // Fallback to original action
  }

  return displayText;
}

// UI updates are handled by audio.js
