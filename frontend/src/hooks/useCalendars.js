import { useQuery } from '@tanstack/react-query'
import api from '../api'

export function useCalendars() {
  return useQuery({
    queryKey: ['calendars'],
    queryFn: api.getCalendars,
    staleTime: Infinity,
  })
}
