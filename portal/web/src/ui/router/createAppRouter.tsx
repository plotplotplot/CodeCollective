import { Navigate, createBrowserRouter } from 'react-router-dom'
import { AppLayout } from '../shell/AppLayout'
import App from '../../App'
import { EconomicOpsPage } from '../views/EconomicOpsPage'
import { AuthCallbackPage } from '../views/AuthCallbackPage'
import { InitiativeDetailPage } from '../views/InitiativeDetailPage'
import { InitiativeSignPage } from '../views/InitiativeSignPage'
import { ConstituentAccountPage } from '../views/constituent/ConstituentAccountPage'
import { ConstituentProfilePage } from '../views/constituent/ConstituentProfilePage'
import { ConstituentLoginPage } from '../views/constituent/ConstituentLoginPage'
import { ConstituentRegisterPage } from '../views/constituent/ConstituentRegisterPage'
import { CampaignLoginPage } from '../views/campaign/CampaignLoginPage'
import { CampaignRegisterPage } from '../views/campaign/CampaignRegisterPage'
import { CampaignInitiativesPage } from '../views/campaign/CampaignInitiativesPage'
import { CampaignInitiativeEditorPage } from '../views/campaign/CampaignInitiativeEditorPage'
import { CampaignInitiativeBallotPage } from '../views/campaign/CampaignInitiativeBallotPage'
import { CampaignProfilePage } from '../views/campaign/CampaignProfilePage'
import { CampaignAccountPage } from '../views/campaign/CampaignAccountPage'
import { PublicCampaignManagerPage } from '../views/public/PublicCampaignManagerPage'
import { NotFoundPage } from '../views/NotFoundPage'
import { AboutPage } from '../views/AboutPage'
import { DashboardPage } from '../dashboard/DashboardPage'
import { AdminPage } from '../views/AdminPage'
import { TargetPage } from '../views/TargetPage'
import { CampaignEditableInitiativesPage } from '../views/campaign/CampaignEditableInitiativesPage'
import { SendPage } from '../views/SendPage'
import { ReceivePage } from '../views/ReceivePage'
import { CreatePage } from '../views/CreatePage'
import { CreateForProfitPage } from '../views/CreateForProfitPage'
import { CreateNonProfitPage } from '../views/CreateNonProfitPage'

export function createAppRouter() {
  const baseUrl = import.meta.env.BASE_URL ?? '/'
  const basename = baseUrl === '/' ? '/' : baseUrl.replace(/\/$/, '')

  return createBrowserRouter(
    [
      { path: '/', element: <App /> },
      { path: '/ecops', element: <EconomicOpsPage /> },
      { path: '/send', element: <SendPage /> },
      { path: '/receive', element: <ReceivePage /> },
      { path: '/create', element: <CreatePage /> },
      { path: '/create/for-profit', element: <CreateForProfitPage /> },
      { path: '/create/non-profit', element: <CreateNonProfitPage /> },
      { path: '/auth/callback', element: <AuthCallbackPage /> },
      // If someone hits the physical file path in S3/CloudFront, redirect to the SPA root.
      { path: '/index.html', element: <Navigate to="/" replace /> },
      {
        element: <AppLayout />,
        children: [
          { path: '/initiatives/:slug', element: <InitiativeDetailPage /> },
          { path: '/initiatives/:slug/sign', element: <InitiativeSignPage /> },

          { path: '/about', element: <AboutPage /> },

          // Constituent
          { path: '/constituent/register', element: <ConstituentRegisterPage /> },
          { path: '/constituent/login', element: <ConstituentLoginPage /> },
          { path: '/constituent/dashboard', element: <DashboardPage /> },
          { path: '/constituent/profile', element: <ConstituentProfilePage /> },
          { path: '/constituent/account', element: <ConstituentAccountPage /> },

          // Campaign manager (demo pages: static but navigable)
          { path: '/campaign/register', element: <CampaignRegisterPage /> },
          { path: '/campaign/login', element: <CampaignLoginPage /> },
          { path: '/campaign/initiatives', element: <CampaignInitiativesPage /> },
          { path: '/campaign/initiatives/editable', element: <CampaignEditableInitiativesPage /> },
          { path: '/campaign/initiatives/new', element: <CampaignInitiativeEditorPage /> },
          { path: '/campaign/initiatives/:id/edit', element: <CampaignInitiativeEditorPage /> },
          { path: '/campaign/initiatives/:id/ballot', element: <CampaignInitiativeBallotPage /> },
          { path: '/campaign/profile', element: <CampaignProfilePage /> },
          { path: '/campaign/account', element: <CampaignAccountPage /> },
          { path: '/admin', element: <AdminPage /> },
          { path: '/targets/:target', element: <TargetPage /> },

          // Public profile
          { path: '/campaign-managers/:handle', element: <PublicCampaignManagerPage /> },

          { path: '*', element: <NotFoundPage /> },
        ],
      },
    ],
    { basename },
  )
}
