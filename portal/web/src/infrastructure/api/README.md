# API Infrastructure

This module provides repository implementations that communicate with the backend API for persistence.

## Architecture

Following **Hexagonal Architecture** (Ports and Adapters):

- **Ports**: Interfaces in `src/application/ports/`
- **Adapters**: Implementations in `src/infrastructure/api/`
- **Domain**: Business logic in `src/domain/`

## Usage

### Configuration

Set environment variables in your `.env` file:

```bash
# Use 'mock' for localStorage, 'api' for backend
VITE_DATA_SOURCE=api

# API base URL (optional, defaults to '/api/governance')
VITE_API_BASE_URL=/api/governance
```

### Creating Services

```typescript
import { createServices } from './composition/createServices'

// Uses environment configuration
const services = createServices()

// Or with explicit configuration
const services = createServices({
  dataSource: 'api',
  apiBaseUrl: '/api/governance'
})
```

### Error Handling

The API repository throws typed errors:

```typescript
import { 
  APIEngagementRepository, 
  AuthenticationError, 
  NotFoundError,
  APIError 
} from './infrastructure/api'

const repo = new APIEngagementRepository('/api/governance')

try {
  await repo.addComment({ motionId: '123', authorId: 'user1', authorName: 'User', body: 'Hello' })
} catch (error) {
  if (error instanceof AuthenticationError) {
    // Redirect to login
  } else if (error instanceof NotFoundError) {
    // Show 404
  } else if (error instanceof APIError) {
    // Generic API error
    console.error(error.statusCode, error.message)
  }
}
```

## Available Endpoints

### Engagement

- `POST /motions/{id}/upvote` - Toggle upvote
- `POST /motions/{id}/downvote` - Toggle downvote
- `GET /motions/{id}/user-vote` - Get user's vote
- `GET /motions/{id}/vote-counts` - Get vote counts
- `GET /motions/{id}/comments` - List comments
- `POST /motions/{id}/comments` - Add comment

## Features

- ✅ Request timeout handling (30s default)
- ✅ Proper error types for different HTTP status codes
- ✅ Input sanitization (URL encoding)
- ✅ Structured logging (dev only)
- ✅ Type-safe API responses
- ✅ Automatic auth token injection from sessionStorage
