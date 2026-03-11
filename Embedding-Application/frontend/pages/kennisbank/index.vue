<script setup lang="ts">
definePageMeta({
  middleware: 'auth',
});

await navigateTo('/kennisbank/library', { replace: true });
</script>
