import { mount } from 'svelte'
import './styles/tokens.css'
import './styles/global.css'
import App from './App.svelte'

const target = document.getElementById('root')
if (!target) throw new Error('Root element #root not found')

const app = mount(App, { target })

export default app
