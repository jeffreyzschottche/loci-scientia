<template>
  <div class="h-full w-screen overflow-hidden" style="max-width: 100vw;">
    <Head>
      <Title>AITJE</Title>
      <Meta name="description" :content="t('app.metaDescription')" />
    </Head>
    <NuxtPage />
  </div>
</template>

<script setup lang="ts">
import { useI18n } from '~/composables/useI18n'

const { t } = useI18n()
</script>
