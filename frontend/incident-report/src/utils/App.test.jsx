import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App.jsx'
import { resetReportIdSequence } from './reportId.js'

describe('Report Emergency form', () => {
  beforeEach(() => {
    resetReportIdSequence(0)
  })

  it('submits a citizen report and shows the raw_report preview', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.type(
      screen.getByRole('textbox', { name: 'Location' }),
      'Raj Nagar Extension, Ghaziabad',
    )
    await user.type(
      screen.getByRole('textbox', { name: 'Describe what is happening' }),
      'Water has entered several houses. Around 30 people are trapped and two people are injured.',
    )
    await user.type(screen.getByLabelText('Approx. affected people'), '30')
    await user.type(screen.getByLabelText('Approx. injured people'), '2')

    const yesButtons = screen.getAllByRole('radio', { name: 'Yes' })
    await user.click(yesButtons[0])
    await user.click(yesButtons[1])
    await user.click(screen.getByRole('button', { name: 'SUBMIT REPORT' }))

    expect(await screen.findByText('Report submitted successfully')).toBeInTheDocument()
    expect(screen.getByText(/"report_id": "R001"/)).toBeInTheDocument()
    expect(screen.getByText(/"source_type": "citizen"/)).toBeInTheDocument()
    expect(screen.getByText(/"people_trapped": true/)).toBeInTheDocument()
    expect(screen.getByText(/"medical_emergency": true/)).toBeInTheDocument()
  })

  it('blocks submission when location is missing', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.type(
      screen.getByRole('textbox', { name: 'Describe what is happening' }),
      'Need immediate help at this location.',
    )
    await user.click(screen.getByRole('button', { name: 'SUBMIT REPORT' }))

    expect(
      screen.getByText('Please provide a location or allow access to your current location.'),
    ).toBeInTheDocument()
    expect(screen.queryByText('Report submitted successfully')).not.toBeInTheDocument()
  })

  it('handles geolocation permission denial without crashing', async () => {
    const user = userEvent.setup()
    vi.stubGlobal('navigator', {
      ...navigator,
      geolocation: {
        getCurrentPosition: (_success, error) => {
          error({ code: 1, message: 'denied' })
        },
      },
    })

    render(<App />)
    await user.click(screen.getByRole('button', { name: /use my current location/i }))

    expect(
      screen.getByText('Location permission was denied. Please enter a location instead.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Report Emergency' })).toBeInTheDocument()

    vi.unstubAllGlobals()
  })
})
