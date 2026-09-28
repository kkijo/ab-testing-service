#!/bin/bash
EXP_ID=$(curl -s -X POST http://127.0.0.1:8000/experiments \
  -H "Content-Type: application/json" \
  -d '{"name":"Homepage CTA button test","description":"Compare red vs green call-to-action button"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['id'])")

echo "Создан эксперимент #$EXP_ID"

curl -s -X POST "http://127.0.0.1:8000/experiments/$EXP_ID/variants" \
  -H "Content-Type: application/json" \
  -d '{"name":"control","weight":0.5,"is_control":true}' > /dev/null

curl -s -X POST "http://127.0.0.1:8000/experiments/$EXP_ID/variants" \
  -H "Content-Type: application/json" \
  -d '{"name":"treatment","weight":0.5,"is_control":false}' > /dev/null

echo "Созданы варианты: control, treatment"

echo "Назначаем 200 пользователей..."
for i in $(seq 1 200); do
  curl -s -X POST http://127.0.0.1:8000/assign \
    -H "Content-Type: application/json" \
    -d "{\"experiment_id\": $EXP_ID, \"user_id\": \"user_$i\"}" \
    > /dev/null
done

echo "Симулируем события..."
for i in $(seq 1 100); do
  if [ $((i % 3)) -eq 0 ]; then
    curl -s -X POST http://127.0.0.1:8000/events \
      -H "Content-Type: application/json" \
      -d "{\"experiment_id\": $EXP_ID, \"user_id\": \"user_$i\", \"event_type\": \"click\"}" \
      > /dev/null
  fi
done

echo "Готово. Эксперимент #$EXP_ID"
echo "Открой: http://127.0.0.1:8000/experiments/$EXP_ID/stats"