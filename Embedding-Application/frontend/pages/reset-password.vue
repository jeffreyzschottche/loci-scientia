<script setup lang="ts">
const route = useRoute();

await navigateTo({ path: '/account/reset-password', query: route.query }, { replace: true });
</script>
