import { Card, Divider, Progress, Tag, Typography, theme } from 'antd'
import type { Rating } from '../api/types'
import { LEVELS, LevelTag, ScoreRing } from '../ui'

interface RatingPanelProps {
  rating: Rating
  preview?: boolean
}

export function RatingPanel({ rating, preview = false }: RatingPanelProps) {
  const { token } = theme.useToken()
  const color = LEVELS[rating.level].color

  return (
    <Card className="rating-panel" title={preview ? 'Прогноз рейтинга' : 'Рейтинг задачи'}>
      <div className="rating-summary">
        {preview && <Tag>Прогноз</Tag>}
        <ScoreRing score={rating.total} level={rating.level} type="circle" size={164} />
        <Typography.Text type="secondary">из 100 баллов</Typography.Text>
        <LevelTag level={rating.level} label={rating.level_label} showClarification />
        {preview && (
          <Typography.Text type="secondary" className="rating-preview-note">
            Засчитывается после подтверждения карточки
          </Typography.Text>
        )}
      </div>

      <div className="rating-scale" aria-label="Шкала рейтинга от 0 до 100, пороги уровней: 40, 70 и 90">
        <Progress percent={rating.total} showInfo={false} strokeColor={color} size="small" />
        <div className="rating-scale-marks" style={{ color: token.colorTextSecondary }} aria-hidden="true">
          {[0, 40, 70, 90, 100].map((mark) => (
            <span key={mark} className="rating-scale-mark" style={{ left: `${mark}%` }}>{mark}</span>
          ))}
        </div>
      </div>
      {rating.next_level && (
        <Typography.Paragraph className="rating-next-level">
          До уровня «{rating.next_level.label}» не хватает {rating.next_level.points_needed} баллов
        </Typography.Paragraph>
      )}

      <Divider />
      <Typography.Title level={5}>Из чего складывается рейтинг</Typography.Title>
      {rating.categories.length === 0 ? (
        <Typography.Paragraph type="secondary">Разбивка рейтинга пока недоступна</Typography.Paragraph>
      ) : (
        <ul className="rating-categories">
          {rating.categories.map((category) => (
            <li key={category.key}>
              <div className="rating-category-heading">
                <Typography.Text strong>{category.label}</Typography.Text>
                <Typography.Text strong className="rating-category-score">
                  {category.earned}/{category.max}
                </Typography.Text>
              </div>
              <ul className="rating-checks">
                {category.checks.map((check, index) => (
                  <li key={`${check.field}-${index}`}>
                    <span
                      className="rating-check-icon"
                      style={{ color: check.passed ? token.colorSuccess : token.colorTextTertiary }}
                      aria-label={check.passed ? 'Выполнено' : 'Не выполнено'}
                    >
                      {check.passed ? '✓' : '○'}
                    </span>
                    <Typography.Text>{check.label}</Typography.Text>
                    <Typography.Text type="secondary" className="rating-check-points">
                      {check.passed ? check.points : 0}/{check.points}
                    </Typography.Text>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      )}

      <Divider />
      <Typography.Title level={5}>Что повысит рейтинг</Typography.Title>
      <Typography.Paragraph strong>
        Все пункты → {rating.total + rating.missing.reduce((sum, item) => sum + item.points, 0)} баллов
      </Typography.Paragraph>
      {rating.missing.length > 0 ? (
        <ul className="rating-missing">
          {rating.missing.map((item, index) => (
            <li key={`${item.field}-${index}`}>
              <Typography.Text>{item.hint}</Typography.Text>
              <Tag className="rating-points-tag" style={{ color: token.colorPrimary }}>+{item.points}</Tag>
            </li>
          ))}
        </ul>
      ) : (
        <Typography.Paragraph type="secondary">
          {rating.total === 100 ? 'Все проверки пройдены' : 'Подсказок для улучшения пока нет'}
        </Typography.Paragraph>
      )}
    </Card>
  )
}
