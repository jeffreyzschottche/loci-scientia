<script setup lang="ts">
const route = useRoute();

await navigateTo({ path: '/account/forgot-password', query: route.query }, { replace: true });
</script>
