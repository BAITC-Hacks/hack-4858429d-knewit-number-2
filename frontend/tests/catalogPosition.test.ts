import assert from 'node:assert/strict'
import test from 'node:test'
import { predictCatalogPosition } from '../src/lib/catalogPosition.ts'
import type { CatalogItem } from '../src/api/types.ts'

const catalog: CatalogItem[] = [95, 81, 66, 48, 25].map((score, index) => ({
  id: index + 1, position: index + 1, rating_total: score,
  title: 'Тест', industry: 'IT', business_name: 'Тест', need_short: '',
  level: 'working', level_label: 'Тестовая подпись API', needs_clarification: false,
  proposals_count: 0, published_at: `2026-09-23T10:00:0${index}+00:00`,
}))

test('new task forecast uses the whole catalog, with existing ties ahead', () => {
  assert.equal(predictCatalogPosition(65, catalog), 4)
  assert.equal(predictCatalogPosition(90, catalog), 2)
  assert.equal(predictCatalogPosition(81, catalog), 3)
  assert.equal(predictCatalogPosition(0, catalog), 6)
  assert.equal(predictCatalogPosition(100, []), 1)
})

test('published task excludes itself and retains publication order on equal scores', () => {
  assert.equal(predictCatalogPosition(66, catalog, catalog[2]), 3)
  assert.equal(predictCatalogPosition(95, catalog, catalog[2]), 2)
  assert.equal(predictCatalogPosition(66, catalog, catalog[0]), 2)
  const simultaneous = catalog.map((item) => ({ ...item, rating_total: 70, published_at: catalog[0].published_at }))
  assert.equal(predictCatalogPosition(70, simultaneous, simultaneous[2]), 3)
})
