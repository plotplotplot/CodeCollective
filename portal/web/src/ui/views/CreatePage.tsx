import { Link } from 'react-router-dom'
import { Header } from '../shell/Header'
import { Footer } from '../shell/Footer'

export function CreatePage() {
  return (
    <div className="portal-shell">
      <Header />
      <main className="portal-main">
        <div className="portal-container">
          <section className="portal-hero">
            <div>
              <span className="portal-pill">Entity Management</span>
              <h1>Create entity</h1>
              <p className="portal-muted">Create a for-profit business or non-profit organization account.</p>
            </div>
          </section>

          <section className="portal-section" id="create">
            <div className="portal-grid">
              <Link to="/create/for-profit" className="portal-card" style={{ display: 'grid', gap: 10 }}>
                <span className="portal-pill">Entity Type</span>
                <h2 style={{ margin: 0 }}>For Profit</h2>
                <p className="portal-muted">Create a business entity.</p>
              </Link>
              <Link to="/create/non-profit" className="portal-card" style={{ display: 'grid', gap: 10 }}>
                <span className="portal-pill">Entity Type</span>
                <h2 style={{ margin: 0 }}>Non Profit</h2>
                <p className="portal-muted">Create a nonprofit and assemble a board from users.</p>
              </Link>
            </div>
          </section>
        </div>
      </main>
      <Footer />
    </div>
  )
}
