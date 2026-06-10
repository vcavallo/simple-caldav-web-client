import { useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api'

// Event fetching itself is driven by FullCalendar's `events` function (see
// CalendarView), so here we expose only the mutations plus a refetch helper.
export function useEventMutations(onError) {
  const qc = useQueryClient()

  const invalidate = () => qc.invalidateQueries({ queryKey: ['events'] })

  const create = useMutation({
    mutationFn: (payload) => api.createEvent(payload),
    onSuccess: invalidate,
    onError,
  })

  const update = useMutation({
    mutationFn: ({ id, payload }) => api.updateEvent(id, payload),
    onSuccess: invalidate,
    onError,
  })

  const remove = useMutation({
    mutationFn: ({ id, url, etag }) => api.deleteEvent(id, { url, etag }),
    onSuccess: invalidate,
    onError,
  })

  return { create, update, remove, invalidate }
}
