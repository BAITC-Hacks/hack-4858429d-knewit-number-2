// Run only against an isolated local test database: this script creates tasks and proposals.
import assert from 'node:assert/strict'

const base = process.env.TASKREADY_TEST_API
if (!base || !['localhost', '127.0.0.1'].includes(new URL(base).hostname)) {
  throw new Error('Set TASKREADY_TEST_API to an isolated local backend, e.g. http://localhost:8001')
}

const calls = new Set()
async function request(method, path, body, expected = 200) {
  const response = await fetch(`${base}/api${path}`, {
    method, headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const data = await response.json()
  assert.equal(response.status, expected, `${method} ${path}: ${JSON.stringify(data)}`)
  if (expected >= 400) assert.equal(typeof data.detail, 'string')
  calls.add(`${method} ${path.split('?')[0].replace(/\/\d+/g, '/{id}')}`)
  return data
}

const industries = await request('GET', '/industries')
const examples = await request('GET', '/examples/drafts')
const teams = await request('GET', '/teams')
assert.equal(industries.length, 10)
assert.equal(examples.length, 5)
assert.equal(teams.length, 5)
const catalog = await request('GET', '/catalog')
assert.ok(catalog.length >= 5)
assert.deepEqual(catalog.map((item) => item.position), catalog.map((_, index) => index + 1))
for (const item of catalog) {
  const filtered = await request('GET', `/catalog?industry=${encodeURIComponent(item.industry)}&level=${item.level}`)
  assert.deepEqual(filtered.find((row) => row.id === item.id), item)
}
await request('GET', '/tasks/999999999', undefined, 404)
await request('POST', '/tasks', { draft_text: 'short', industry: 'IT' }, 422)
let task = await request('POST', '/tasks', { draft_text: examples[0].text, industry: examples[0].industry, business_name: 'API smoke test' })
const path = `/tasks/${task.id}`
assert.equal(task.status, 'clarifying')
assert.ok(task.questions.length >= 3 && task.questions.length <= 5)
assert.equal(task.rating, null)
await request('POST', `${path}/publish`, undefined, 400)
await request('POST', `${path}/answers`, { answers: [] }, 422)
task = await request('POST', `${path}/answers`, { answers: task.questions.map((question, index) => ({ question_id: question.id, answer: index === 0 ? 'Выгрузка данных за 12 месяцев в CSV' : '' })) })
assert.equal(task.status, 'card_ready')
const card = {
  title: 'Интеграционный тест API',
  context: 'Мы небольшая сеть кофеен в Алматы. Продажи в будние дни падают, хотим понять почему и что делать.',
  need: 'Хотим понять причины падения продаж в будние дни и повысить выручку каждой кофейни.',
  users: 'Управляющие кофейнями и маркетолог', data: 'Выгрузка чеков за 12 месяцев в CSV',
  expected_result: 'Дашборд продаж по дням и часам с детализацией каждой кофейни и три рекомендации для маркетолога',
  constraints: '', success_criteria: '', contact: 'demo@example.com', interaction_format: '',
}
const preview = await request('POST', '/rating/preview', card)
assert.equal(preview.total, 65)
assert.equal((await request('GET', path)).rating, null)
await request('PUT', `${path}/card`, { ...card, title: 'a' }, 422)
task = await request('PUT', `${path}/card`, card)
assert.deepEqual(task.rating, preview)
assert.equal(task.status, 'confirmed')
task = await request('POST', `${path}/publish`)
assert.equal(task.status, 'published')
assert.ok(task.position > 0)
await request('POST', `${path}/publish`, undefined, 400)
const updated = await request('PUT', `${path}/card`, { ...card, success_criteria: 'Рост выручки на 15% за 2 месяца', constraints: 'Срок 6 недель, Python, доступ после NDA' })
assert.equal(updated.rating.total, 90)
assert.equal(updated.rating.level, 'priority')
assert.deepEqual(updated.rating_history.map((item) => item.total), [65, 90])
assert.ok(updated.position < task.position)

const proposal = { team_id: teams[0].id, idea: 'Проанализируем продажи кофеен', plan: 'Подготовим отчёт и рекомендации', deadline: '6 недель', prototype_url: 'https://example.com/prototype' }
await request('POST', `${path}/proposals`, { ...proposal, idea: 'short' }, 422)
await request('POST', `${path}/proposals`, { ...proposal, prototype_url: 'javascript:alert(1)' }, 422)
const first = await request('POST', `${path}/proposals`, proposal)
const second = await request('POST', `${path}/proposals`, { ...proposal, team_id: teams[1].id })
await request('POST', `/proposals/${first.id}/milestone`, undefined, 400)
for (const item of [first, second]) await request('POST', `/proposals/${item.id}/decision`, { decision: 'selected' })
assert.ok((await request('GET', `${path}/proposals`)).every((item) => item.status === 'selected'))
const milestone = await request('POST', `/proposals/${first.id}/milestone`)
assert.equal(milestone.milestones_confirmed, 1)
const updatedTeams = await request('GET', '/teams')
assert.equal(updatedTeams.find((team) => team.id === teams[0].id).points, teams[0].points + 10)
await request('POST', `/proposals/${second.id}/decision`, { decision: 'rejected' })
const replies = await request('GET', `${path}/proposals`)
assert.deepEqual(replies.map((item) => item.status), ['selected', 'rejected'])
assert.equal((await request('GET', path)).proposals_count, 2)
assert.ok((await request('GET', '/tasks')).some((item) => item.id === task.id))
const recommendations = await request('GET', `/teams/${teams[0].id}/recommendations`)
assert.ok(Array.isArray(recommendations))
assert.ok(recommendations.every(({ task: item }) => item.rating_total >= 40))
if (!recommendations.length) console.log('NOTE: recommendations API returned []; the route may still be a backend stub.')
console.log(`PASS: ${calls.size} API routes; draft → answers → preview → confirm → publish → edit → proposals → decisions → milestone.`)
