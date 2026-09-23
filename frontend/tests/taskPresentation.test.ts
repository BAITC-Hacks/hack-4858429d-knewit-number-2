import assert from 'node:assert/strict'
import test from 'node:test'
import { parseTaskId, ratingChangeText, safeExternalUrl, taskTitle } from '../src/lib/taskPresentation.ts'
import type { Task } from '../src/api/types.ts'

test('only positive safe integer IDs are sent to the API', () => {
  assert.equal(parseTaskId('42'), 42)
  for (const value of ['', '0', '-1', 'abc', '1.2', '1e3', '01', '9007199254740992', null, undefined]) {
    assert.equal(parseTaskId(value), null)
  }
})

test('prototype links only accept http(s), not executable or credential-bearing URLs', () => {
  assert.equal(safeExternalUrl(' https://example.com/prototype '), 'https://example.com/prototype')
  assert.equal(safeExternalUrl('http://example.com'), 'http://example.com/')
  for (const value of ['', '/tasks/1', 'javascript:alert(1)', 'data:text/html,test', 'ftp://example.com', 'https://user:pass@example.com']) {
    assert.equal(safeExternalUrl(value), null)
  }
})

test('notifications preserve previous server values and distinguish missing rating from zero', () => {
  const before = { rating: { total: 65 }, position: 4 } as Task
  const after = { rating: { total: 90 }, position: 2 } as Task
  assert.equal(ratingChangeText(before, after), 'Рейтинг 65 → 90, место #4 → #2')
  assert.equal(ratingChangeText({ rating: null, position: null } as Task, { rating: { total: 0 }, position: null } as Task), 'Рейтинг — → 0, место — → —')
  assert.equal(before.rating?.total, 65)
})

test('untitled drafts still have an identifiable link in My tasks', () => {
  assert.equal(taskTitle({ id: 7, card: { title: '  ' } } as Task), 'Черновик №7')
  assert.equal(taskTitle({ id: 7, card: { title: '  Анализ продаж  ' } } as Task), 'Анализ продаж')
})
