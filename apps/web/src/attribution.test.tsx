import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { expect, test } from 'vitest'
import { Layout } from './components'

test('renders the attribution line when the payload includes it', () => {
  const payload = { attribution: { text: 'Data provided by Marvel. © 2026 MARVEL' } }
  render(
    <MemoryRouter>
      <Layout attribution={payload.attribution}>content</Layout>
    </MemoryRouter>,
  )
  expect(screen.getAllByText('Data provided by Marvel. © 2026 MARVEL').length).toBeGreaterThan(0)
})
