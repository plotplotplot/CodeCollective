
import { getAI, getGenerativeModel, GoogleAIBackend } from "https://www.gstatic.com/firebasejs/11.10.0/firebase-ai.js";
import { firebaseConfig } from './firebase-config.js';
import { initializeApp } from "https://www.gstatic.com/firebasejs/11.10.0/firebase-app.js";

// Initialize Firebase AI
console.log('Initializing Firebase app...');
const firebaseApp = initializeApp(firebaseConfig);
console.log('Firebase app initialized, setting up AI service...');
const ai = getAI(firebaseApp, { backend: new GoogleAIBackend() });
console.log('AI service initialized, creating model...');
//const model = getGenerativeModel(ai, { model: "gemini-2.5-flash" });
//const model = getGenerativeModel(ai, { model: "gemini-2.0-flash-lite" });
const model = getGenerativeModel(ai, { model: "gemini-2.5-flash-lite-preview-06-17" });

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
  const orderContainer = document.getElementById('orderTable');
  if (!orderContainer) return;

  // Clear existing content
  orderContainer.innerHTML = '';

  // Add order items
  userOrder.forEach(item => {
    const itemName = Object.keys(item)[0];
    const notes = item[itemName];
    const baseName = itemName.split(' #')[0]; // Remove item number
    
    // Find price from menu
    let price = '';
    if (menu[activeService]) {
      for (const menuItem of menu[activeService]) {
        if (Object.keys(menuItem)[0] === baseName) {
          price = menuItem[baseName][1]; // Get price from menu
          break;
        }
      }
    }

    const itemDiv = document.createElement('div');
    itemDiv.className = 'order-item';
    
    itemDiv.innerHTML = `
      <div class="order-item-name">${itemName}</div>
      <div class="order-item-notes">${notes || 'No notes'}</div>
      <div class="order-item-price">${price}</div>
    `;
    
    orderContainer.appendChild(itemDiv);
  });

  // Add total if items exist
  if (userOrder.length > 0) {
    const totalDiv = document.createElement('div');
    totalDiv.className = 'order-total';
    
    // Calculate total
    let total = 0;
    userOrder.forEach(item => {
      const itemName = Object.keys(item)[0];
      const baseName = itemName.split(' #')[0];
      
      if (menu[activeService]) {
        for (const menuItem of menu[activeService]) {
          if (Object.keys(menuItem)[0] === baseName) {
            const priceStr = menuItem[baseName][1];
            if (priceStr !== 'Included') {
              total += parseFloat(priceStr.replace('$', ''));
            }
            break;
          }
        }
      }
    });
    
    totalDiv.textContent = `Total: $${total.toFixed(2)}`;
    orderContainer.appendChild(totalDiv);
  }
}

export async function processUserRequest(requestText, conversationHistory = []) {
  // Get current menu data
  const response = await fetch('./menu.json');
  const menu = await response.json();
  
  // Format conversation history with clear speaker labels
  const historyContext = conversationHistory
    .slice(-5) // Keep last 5 exchanges
    .map(msg => `=== ${msg.speaker.toUpperCase()} ===\n${msg.text}`)
    .join('\n\n');

// Update prompt with current data and history
const currentPrompt = `
=== CONVERSATION HISTORY ===
${historyContext}

Current Context:
Available services: ${availableServices.map(s => `- ${s}`).join('\n')}
Current service: ${activeService}
User Order: ${userOrder.map(s => `- ${s}`).join('\n')}
Menu items: ${JSON.stringify(menu[activeService] || [])}

User said: "${requestText}"

Please respond with one of these actions:
- CHANGE_SERVICE [service name]
- ADD_ITEM [item name], [note]
- REMOVE_ITEM [item name] #[number]
- ADD_NOTE [note]
- POPULAR_ITEMS
- POPULAR_SERVICES
- REQUEST_CONFIRMATION
- SUBMIT_ORDER
- CLEAR_ORDER

Rules:
1. Return only the action
2. Use exact item names from menu
3. Use exact service names from list
4. You must send REQUEST_CONFIRMATION before SUBMIT_ORDER — this is mandatory
5. Never send SUBMIT_ORDER unless REQUEST_CONFIRMATION has already been sent in a previous message
6. After sending REQUEST_CONFIRMATION, wait for a clear user confirmation (e.g., "submit", "yes", "okay", "buy this", "place order") before sending SUBMIT_ORDER
7. Never send REQUEST_CONFIRMATION if the last action was REQUEST_CONFIRMATION
8. If the user gives confirmation but REQUEST_CONFIRMATION has not yet been sent, respond with REQUEST_CONFIRMATION (not SUBMIT_ORDER)
9. Do not repeat or rephrase existing notes for items
10. Use ADD_NOTE only if it adds meaningful new information not already attached to any item
11. Do not include the square brackets above

Important:
- You must enforce the sequence: REQUEST_CONFIRMATION → user confirmation → SUBMIT_ORDER
- Do not break this sequence or repeat REQUEST_CONFIRMATION unnecessarily.`;



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
    updateOrderDisplay();
    displayText = `Added ${itemName} to your order`;
  } 
  else if (action.startsWith('REMOVE_ITEM')) {
    const itemKey = action.replace('REMOVE_ITEM', '').trim();
    userOrder = userOrder.filter(item => !Object.keys(item)[0].includes(itemKey));
    updateOrderDisplay();
    displayText = `Removed ${itemKey} from your order`;
  }
  else if (action.startsWith('ADD_NOTE')) {
    const note = action.replace('ADD_NOTE', '').trim();
    if (userOrder.length > 0) {
      const lastItem = userOrder[userOrder.length - 1];
      const key = Object.keys(lastItem)[0];
      lastItem[key] = note;
      updateOrderDisplay();
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
  else if (action === 'CLEAR_ORDER') {
    userOrder = [];
    updateOrderDisplay();
    displayText = 'Order cleared';
  }
  else if (action === 'PRINT_ORDER') {
    if (userOrder.length === 0) {
      displayText = 'Your order is currently empty';
    } else {
      let orderText = '=== CURRENT ORDER ===\n';
      let total = 0;
      
      userOrder.forEach(item => {
        const itemName = Object.keys(item)[0];
        const notes = item[itemName];
        const baseName = itemName.split(' #')[0];
        let price = '';
        
        // Get price from menu
        if (menu[activeService]) {
          for (const menuItem of menu[activeService]) {
            if (Object.keys(menuItem)[0] === baseName) {
              price = menuItem[baseName][1];
              if (price !== 'Included') {
                total += parseFloat(price.replace('$', ''));
              }
              break;
            }
          }
        }

        orderText += `- ${itemName}`;
        if (notes) {
          orderText += ` (${notes})`;
        }
        if (price) {
          orderText += ` - ${price}`;
        }
        orderText += '\n';
      });

      orderText += `\nTOTAL: $${total.toFixed(2)}`;
      displayText = orderText;
    }
  }
  else {
    displayText = action; // Fallback to original action
  }

  return displayText;
}

// UI updates are handled by audio.js
